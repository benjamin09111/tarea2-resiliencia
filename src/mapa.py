"""Mapa Leaflet (folium) con la infraestructura, el dano del terremoto y los ATTR. Todo se lee de la BD."""
import argparse
import json
import math
from pathlib import Path

import branca.colormap as cm
import folium

from src.db import conectar

RAIZ = Path(__file__).resolve().parent.parent
COMA = lambda v, d=4: f"{v:.{d}f}".replace(".", ",")
# capas sinteticas: color, trazo
ESTILO = {
    "acometida": ("#7B3294", "6 4", 1.6, "Acometidas (sintéticas)"),
    "postacion": ("#7F7F7F", "5 5", 1.0, "Postación eléctrica (sintética)"),
    "camino": ("#8C564B", "5 5", 1.0, "Caminos (sintéticos)"),
    "ferry": ("#1F77B4", "1 5", 2.0, "Ferry (sintético)"),
}
ROL = {"genera": "#2CA02C", "intercambia": "#FF7F0E", "recibe": "#1F77B4"}


def iso_pga(m, h, alfa):
    r = (m["A"] * math.exp(m["C"] * m["ms_max"]) / alfa) ** (1 / m["B"]) - m["D_km"]
    return math.sqrt(max(r * r - h * h, 0))


def main(salida, centro, zoom, captura=False):
    cfg = json.loads((RAIZ / "config.json").read_text())
    attr = json.loads((RAIZ / "resultados" / "attr.json").read_text())
    with conectar() as con:
        aristas = con.execute(
            "SELECT id, capa, largo_km, prob_falla, pga_max_cms2, dist_epi_km, tasa_cortes, ST_AsGeoJSON(the_geom, 4) FROM red_noded ORDER BY id").fetchall()
        nodos = con.execute("SELECT id, nombre, roles, lat, lon, fuente, coord_aproximada, cobertura FROM nodos_clave ORDER BY id").fetchall()
        sis = con.execute("SELECT mag, profundidad_km, ST_Y(geom), ST_X(geom), lugar, tiempo FROM sismo").fetchone()
    m = folium.Map(location=centro, zoom_start=zoom, tiles=None, control_scale=True, **({"fadeAnimation": False, "zoomAnimation": False} if captura else {}))
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri, HERE, Garmin, OpenStreetMap contributors", name="Mapa base (Esri Light Gray)", max_zoom=16).add_to(m)
    rampa = cm.LinearColormap(["#FFD966", "#F4A100", "#D7301F", "#7F0000"], vmin=0, vmax=1,
                              caption="Probabilidad de falla de la fibra (gris: sin daño)")
    capas = {}
    for k in ("ferry", "camino", "postacion", "acometida"):
        capas[k] = folium.FeatureGroup(name=ESTILO[k][3], show=True)
    capas["fibra"] = folium.FeatureGroup(name="Fibra óptica (color = probabilidad de falla)", show=True)
    feats = {k: [] for k in capas}
    for i, capa, km, p, pga, d, lam, gj in aristas:
        k = "acometida" if capa.startswith("acometida") else capa
        feats[k].append({"type": "Feature", "geometry": json.loads(gj),
                         "properties": {"id": i, "km": COMA(km, 2), "p": p, "pga": "" if pga is None else f"{pga:.0f}",
                                        "dist": COMA(d, 1), "lam": "" if lam is None else COMA(lam, 4), "ps": COMA(p, 4)}})
    for k in ("ferry", "camino", "postacion", "acometida"):
        col, dash, w, _ = ESTILO[k]
        folium.GeoJson({"type": "FeatureCollection", "features": feats[k]},
                       style_function=lambda f, col=col, dash=dash, w=w: {"color": col, "weight": w, "dashArray": dash, "opacity": 0.75},
                       tooltip=folium.GeoJsonTooltip(fields=["id", "km", "dist", "ps"], aliases=["enlace", "km", "dist. al epicentro (km)", "prob. de falla"])).add_to(capas[k])
    folium.GeoJson({"type": "FeatureCollection", "features": feats["fibra"]},
                   style_function=lambda f: {"color": "#9AA5B1" if f["properties"]["p"] == 0 else rampa(f["properties"]["p"]),
                                             "weight": 2.6, "opacity": 0.95},
                   tooltip=folium.GeoJsonTooltip(fields=["id", "km", "dist", "pga", "lam", "ps"],
                                                 aliases=["enlace", "km", "dist. al epicentro (km)", "PGA máx. (cm/s²)", "cortes esperados/km·tramo (λ)", "prob. de falla"])).add_to(capas["fibra"])
    for k in ("ferry", "camino", "postacion", "acometida", "fibra"):
        capas[k].add_to(m)
    rampa.add_to(m)
    # nodos clave
    gn = folium.FeatureGroup(name="Nodos clave (genera / intercambia / recibe)", show=True)
    for nid, nombre, roles, lat, lon, fuente, aprox, cob in nodos:
        rs = roles.split(";")
        col = ROL[rs[0]] if len(rs) == 1 else "#333333"
        c = {red: attr[red]["operacion"]["conectividad_por_nodo"][nid]["conectividad_media"] for red in ("RF", "RE")}
        t = {red: attr[red]["terremoto"]["conectividad_por_nodo"][nid]["conectividad_media"] for red in ("RF", "RE")}
        pop = (f"<b>{nid} {nombre}</b><br>Roles: {roles.replace(';', ', ')}<br>Fuente: {fuente}<br>"
               f"Conectividad media con los demás nodos (antes → después):<br>RF {COMA(c['RF'], 3)} → {COMA(t['RF'], 3)}<br>RE {COMA(c['RE'], 3)} → {COMA(t['RE'], 3)}")
        folium.CircleMarker([lat, lon], radius=6, color="white", weight=1.5, fill=True, fill_color=col, fill_opacity=1,
                            tooltip=f"{nid} {nombre}", popup=folium.Popup(pop, max_width=320)).add_to(gn)
    gn.add_to(m)
    # epicentro y dano (isolineas de PGA)
    gs = folium.FeatureGroup(name="Epicentro y PGA del modelo (círculos de 400, 200 y 100 cm/s²)", show=True)
    mod = cfg["modelo"]
    for alfa in (400, 200, 100):
        r = iso_pga(mod, sis[1], alfa)
        folium.Circle([sis[2], sis[3]], radius=r * 1000, color="#D7301F", weight=1.2, fill=False, dash_array="4 4",
                      tooltip=f"PGA = {alfa} cm/s² a {r:.0f} km del epicentro").add_to(gs)
    folium.Marker([sis[2], sis[3]], icon=folium.Icon(color="red", icon="star"),
                  tooltip=f"Epicentro: M {sis[0]} (Mww), {sis[4]}, profundidad {sis[1]} km").add_to(gs)
    gs.add_to(m)
    folium.LayerControl(collapsed=captura).add_to(m)
    fila = lambda red: (f"<tr><td>{red}</td><td>{COMA(attr[red]['operacion']['attr'])}</td>"
                        f"<td>{COMA(attr[red]['terremoto']['attr'])} ± {COMA(1.96 * attr[red]['terremoto']['ee'])}</td></tr>")
    caja = ("<div style='position:fixed;bottom:24px;left:12px;z-index:9999;background:white;padding:8px 10px;border:1px solid #999;"
            "font:12px sans-serif;box-shadow:0 1px 4px rgba(0,0,0,.3)'><b>ATTR (24 nodos clave, 276 pares)</b>"
            "<table style='border-collapse:collapse;margin-top:4px'><tr><th style='padding-right:10px'>Red</th><th style='padding-right:10px'>Operación</th><th>Terremoto (IC 95 %)</th></tr>"
            f"{fila('RF')}{fila('RE')}</table><div style='margin-top:4px;color:#444'>RF: fibra detectada + acometidas<br>RE: las 4 capas + acometidas<br>Línea continua gruesa: fibra; discontinua: enlaces sintéticos<br>"
            f"Nodos: <span style='color:{ROL['genera']}'>●</span> genera <span style='color:{ROL['intercambia']}'>●</span> intercambia "
            f"<span style='color:{ROL['recibe']}'>●</span> recibe <span style='color:#333'>●</span> varios roles</div></div>")
    m.get_root().html.add_child(folium.Element(caja))
    if captura:  # retrasa el evento load unos segundos para que los tiles terminen de cargar antes de la captura
        m.get_root().html.add_child(folium.Element("<script>var t0=Date.now();while(Date.now()-t0<7000){}</script>"))
    out = Path(salida)
    out.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out))
    print("mapa escrito:", out, f"({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=str(RAIZ / "mapa" / "index.html"))
    ap.add_argument("--centro", type=float, nargs=2, default=[-38.0, -71.5])
    ap.add_argument("--zoom", type=int, default=5)
    ap.add_argument("--captura", action="store_true", help="variante para captura de pantalla (control de capas plegado)")
    a = ap.parse_args()
    main(a.salida, a.centro, a.zoom, a.captura)
