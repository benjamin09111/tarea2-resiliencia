"""Carga el sismo 8,8 (USGS, GeoJSON) en la tabla `sismo`. Descarga el GeoJSON solo si falta."""
import json
import urllib.request
from pathlib import Path

from src.db import conectar

RAIZ = Path(__file__).resolve().parent.parent

CREAR = """
CREATE TABLE IF NOT EXISTS sismo (
  id_usgs text PRIMARY KEY, mag double precision, mag_type text, tiempo timestamptz, lugar text,
  profundidad_km double precision, geojson jsonb, geom geometry(Point, 4326))"""


def main():
    cfg = json.loads((RAIZ / "config.json").read_text())["sismo"]
    ruta = RAIZ / "datos" / "crudos" / f"usgs_{cfg['id_usgs']}.geojson"
    if not ruta.exists():
        print("descargando", cfg["url"])
        with urllib.request.urlopen(cfg["url"], timeout=60) as r:
            ruta.write_bytes(r.read())
    ev = json.loads(ruta.read_text(encoding="utf-8"))
    p = ev["properties"]
    lon, lat, prof = ev["geometry"]["coordinates"]
    with conectar(autocommit=True) as con:
        con.execute(CREAR)
        con.execute(
            "INSERT INTO sismo (id_usgs, mag, mag_type, tiempo, lugar, profundidad_km, geojson, geom) "
            "VALUES (%s, %s, %s, to_timestamp(%s / 1000.0), %s, %s, %s::jsonb, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) "
            "ON CONFLICT (id_usgs) DO UPDATE SET mag = EXCLUDED.mag, mag_type = EXCLUDED.mag_type, "
            "tiempo = EXCLUDED.tiempo, lugar = EXCLUDED.lugar, profundidad_km = EXCLUDED.profundidad_km, "
            "geojson = EXCLUDED.geojson, geom = EXCLUDED.geom",
            (ev["id"], p["mag"], p["magType"], p["time"], p["place"], prof, json.dumps(ev), lon, lat))
    print("sismo cargado:", ev["id"], p["mag"], p["magType"], lon, lat, prof)


if __name__ == "__main__":
    main()
