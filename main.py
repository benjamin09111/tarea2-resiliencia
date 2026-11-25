#!/usr/bin/env python3
"""Tarea 2: resiliencia de la red de fibra chilena ante el terremoto 27F. Orquestador de todo el flujo.

    python3 main.py                # flujo completo desde main.sql (el comando para corregir)
    python3 main.py --desde-cero   # reconstruye main.sql desde los shapefiles SAIP
    python3 main.py --sin-mapa     # no genera ni sirve el mapa
    python3 main.py --bajar        # apaga los contenedores y borra la base de datos

Solo usa la biblioteca estandar; el resto corre en contenedores (docker compose).
Flujo por defecto: BD vacia -> main.sql -> topologia (verificacion) -> sismo -> probabilidades
(recalculadas y comparadas con main.sql) -> ATTR antes y despues -> mapa Leaflet.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
os.chdir(RAIZ)
if hasattr(os, "getuid"):  # los contenedores escriben con el usuario del anfitrion
    os.environ.setdefault("HOST_UID", str(os.getuid()))
    os.environ.setdefault("HOST_GID", str(os.getgid()))

DB = "tarea2"
T0 = time.time()
PASO = [0]


def paso(titulo):
    PASO[0] += 1
    print(f"\n[{PASO[0]}] {titulo}", flush=True)
    return time.time()


def fin(t, extra=""):
    print(f"    listo en {time.time() - t:.1f} s {extra}", flush=True)


def correr(cmd, salida=False, check=True, **kw):
    """Ejecuta un comando; con salida=True devuelve su stdout."""
    r = subprocess.run(cmd, text=True, capture_output=salida, **kw)
    if check and r.returncode != 0:
        if salida:
            sys.stderr.write((r.stdout or "") + (r.stderr or ""))
        sys.exit(f"ERROR: fallo el comando: {' '.join(cmd)}")
    return r.stdout if salida else None


def compose(*args, **kw):
    return correr(["docker", "compose", "--progress", "quiet", *args], **kw)


def psql(sql=None, archivo=None, base=DB, tuplas=False):
    """Ejecuta SQL (o un archivo de /work) con psql dentro del contenedor db."""
    cmd = ["exec", "-T", "db", "psql", "-U", "redes", "-d", base, "-v", "ON_ERROR_STOP=1", "-q"]
    if tuplas:
        cmd += ["-At"]
    cmd += ["-f", f"/work/{archivo}"] if archivo else ["-c", sql]
    return compose(*cmd, salida=True)


def py(modulo, *args):
    """Ejecuta un modulo Python del repositorio dentro del contenedor app."""
    compose("run", "--rm", "-T", "app", "python", "-m", modulo, *args)


def verificar_docker():
    try:
        v = subprocess.run(["docker", "compose", "version"], text=True, capture_output=True)
    except FileNotFoundError:
        v = None
    if v is None or v.returncode != 0:
        sys.exit("ERROR: se necesita Docker con el plugin 'docker compose' (v2).\n"
                 "  Ubuntu: sudo apt install docker.io docker-compose-v2 && sudo usermod -aG docker $USER (reiniciar sesion)\n"
                 "  Windows/macOS: instalar Docker Desktop.")
    print("    " + v.stdout.strip())
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        sys.exit("ERROR: Docker esta instalado pero no responde (daemon apagado o sin permisos para tu usuario).")


def levantar_db():
    compose("build", "-q", "app")
    compose("up", "-d", "--wait", "db")
    print("    base de datos lista (PostgreSQL + PostGIS + pgRouting)")


def base_vacia(extensiones=False):
    psql(f"DROP DATABASE IF EXISTS {DB} WITH (FORCE)", base="postgres")
    psql(f"CREATE DATABASE {DB} TEMPLATE template0", base="postgres")
    if extensiones:
        psql("CREATE EXTENSION postgis; CREATE EXTENSION pgrouting;")
    print(f"    base de datos '{DB}' vacia creada")


def volcar_main_sql():
    cab = ("-- main.sql: infraestructura (red, red_pieza, red_noded + vertices), nodos clave, sismo, parametros y probabilidades de falla.\n"
           f"-- Generado con pg_dump (PostgreSQL 16.9, PostGIS 3.5.2, pgRouting 3.8.0) el {time.strftime('%Y-%m-%d', time.gmtime())} por 'python3 main.py --desde-cero'.\n"
           "-- Carga en una BD vacia: psql -v ON_ERROR_STOP=1 -f main.sql\n")
    dump = compose("exec", "-T", "db", "pg_dump", "-U", "redes", "-d", DB, "--no-owner", "--no-privileges", salida=True)
    (RAIZ / "main.sql").write_text(cab + dump, encoding="utf-8")
    print(f"    main.sql escrito ({(RAIZ / 'main.sql').stat().st_size / 1e6:.1f} MB)")


def desde_cero():
    t = paso("Construye la BD desde los shapefiles SAIP (capas, nodado, topologia, nodos clave)")
    base_vacia(extensiones=True)
    py("src.cargar_saip")
    psql(archivo="sql/01_nodar.sql")
    py("src.nodos_clave")  # reconstruye red_noded (sql/02_red_noded.sql), acometidas y topologia final
    fin(t)
    t = paso("Carga el sismo del USGS")
    py("src.cargar_sismo")
    fin(t)
    t = paso("Calcula las probabilidades de falla de cada enlace")
    py("src.probabilidades")
    fin(t)
    t = paso("Escribe main.sql (pg_dump)")
    volcar_main_sql()
    fin(t)


def desde_main_sql():
    t = paso("Crea la BD vacia y carga main.sql")
    if not (RAIZ / "main.sql").exists():
        sys.exit("ERROR: falta main.sql (usa --desde-cero para reconstruirlo).")
    base_vacia()
    psql(archivo="main.sql")
    n = psql("SELECT count(*) || ' aristas, ' || (SELECT count(*) FROM red_noded_vertices_pgr) || ' vertices, ' "
             "|| (SELECT count(*) FROM nodos_clave) || ' nodos clave, ' || (SELECT count(*) FROM sismo) || ' sismo' FROM red_noded", tuplas=True).strip()
    print(f"    cargado: {n}")
    fin(t)
    t = paso("Topologia: pgr_createTopology (tolerancia 0,0001 grados) sobre una copia; se compara su estructura con la de main.sql")
    psql("DROP TABLE IF EXISTS _topo, _topo_vertices_pgr CASCADE; "
         "CREATE TABLE _topo AS SELECT id, capa, the_geom, NULL::int source, NULL::int target FROM red_noded ORDER BY id;")
    psql("SELECT pgr_createTopology('_topo', 0.0001, 'the_geom', 'id', 'source', 'target', clean := true)", tuplas=True)
    comp = ("SELECT count(DISTINCT component) FROM pgr_connectedComponents('SELECT id, source, target, 1 AS cost, 1 AS reverse_cost FROM {t} {w}')")
    medidas = {}
    for tabla in ("_topo", "red_noded"):
        v = int(psql(f"SELECT count(*) FROM {'_topo_vertices_pgr' if tabla == '_topo' else 'red_noded_vertices_pgr'}", tuplas=True).strip())
        rf = int(psql(comp.format(t=tabla, w="WHERE capa IN (''fibra'', ''acometida'')"), tuplas=True).strip())
        re = int(psql(comp.format(t=tabla, w=""), tuplas=True).strip())
        medidas[tabla] = (v, rf, re)
    psql("DROP TABLE _topo, _topo_vertices_pgr CASCADE")
    (vn, rfn, ren), (vm, rfm, rem) = medidas["_topo"], medidas["red_noded"]
    print(f"    recalculada: {vn} vertices, {rfn} componentes RF, {ren} componentes RE")
    print(f"    main.sql   : {vm} vertices, {rfm} componentes RF, {rem} componentes RE")
    print("    OK: la topologia recalculada coincide con main.sql" if medidas["_topo"] == medidas["red_noded"]
          else "    AVISO: la topologia recalculada difiere de main.sql; se usa la de main.sql")
    fin(t)
    t = paso("Sismo 8,8 (USGS): carga del GeoJSON versionado en la tabla sismo")
    py("src.cargar_sismo")
    fin(t)
    t = paso("Probabilidades de falla: se recalculan con el modelo y se comparan con las de main.sql")
    psql("DROP TABLE IF EXISTS _p_main; CREATE TABLE _p_main AS SELECT id, prob_falla FROM red_noded")
    py("src.probabilidades")
    dif = float(psql("SELECT coalesce(max(abs(a.prob_falla - b.prob_falla)), 0) FROM red_noded a JOIN _p_main b USING (id)", tuplas=True).strip())
    psql("DROP TABLE _p_main")
    print(f"    diferencia maxima con main.sql: {dif:.2e}")
    print("    OK: las probabilidades coinciden con main.sql" if dif < 1e-9 else "    AVISO: las probabilidades difieren de main.sql")
    fin(t)


def attr_y_tabla():
    t = paso("ATTR antes (operacion, exacto) y despues del terremoto (Monte Carlo, N = 10.000, semilla 20100227)")
    (RAIZ / "resultados").mkdir(exist_ok=True)
    salida = RAIZ / "resultados" / "attr.json"
    if salida.exists():
        salida.unlink()
    py("src.attr", "--escenario-falla", "operacion")
    py("src.attr", "--escenario-falla", "terremoto")
    fin(t)
    d = json.loads(salida.read_text(encoding="utf-8"))
    esp = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))["esperados"]
    f = lambda x: f"{x:.4f}".replace(".", ",")
    print("\n    Red | ATTR operacion | ATTR terremoto (IC 95 %)         | Diferencia | Variacion | Coincide con el informe")
    ok = True
    for red in ("RF", "RE"):
        o, te = d[red]["operacion"]["attr"], d[red]["terremoto"]
        coincide = abs(o - esp[red]["operacion"]) < 5e-5 and abs(te["attr"] - esp[red]["terremoto"]) < 5e-5
        ok &= coincide
        post = te["attr"]
        pct = f"{100 * (post - o) / o:+.1f}".replace(".", ",")
        print(f"    {red}  | {f(o)}         | {f(post)} ({f(te['ic95'][0])}-{f(te['ic95'][1])})  | {f(post - o):>9}  | {pct} %   | {'si' if coincide else 'NO'}")
    print("    OK: los valores coinciden con los del informe" if ok else "    AVISO: algun valor no coincide con el informe")


def mapa():
    t = paso("Mapa Leaflet (nodos, enlaces, dano del terremoto, epicentro)")
    py("src.mapa")
    compose("up", "-d", "web")
    fin(t)
    print("    Mapa interactivo: http://localhost:8000/mapa/   (tambien se puede abrir mapa/index.html)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde-cero", action="store_true", help="reconstruye todo desde los shapefiles y reescribe main.sql")
    ap.add_argument("--sin-mapa", action="store_true", help="no genera ni sirve el mapa")
    ap.add_argument("--bajar", action="store_true", help="apaga los contenedores y borra la base de datos")
    a = ap.parse_args()
    if a.bajar:
        verificar_docker()
        compose("down", "-v")
        print("Contenedores apagados y base de datos borrada.")
        return
    t = paso("Comprueba Docker")
    verificar_docker()
    fin(t)
    t = paso("Levanta PostgreSQL + PostGIS + pgRouting (la primera vez descarga la imagen y construye el contenedor Python)")
    levantar_db()
    fin(t)
    if a.desde_cero:
        desde_cero()
    else:
        desde_main_sql()
    attr_y_tabla()
    if not a.sin_mapa:
        mapa()
    print(f"\nTerminado en {time.time() - T0:.0f} s.")


if __name__ == "__main__":
    main()
