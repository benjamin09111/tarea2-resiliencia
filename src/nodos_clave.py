"""Nodos clave (datos/nodos_clave.csv) y acometidas sinteticas tipo PoP. Idempotente.

Cada nodo se une con un segmento recto al vertice mas cercano de cada componente conexa que pase a
<= d_max. RF: componentes de fibra (capa 'acometida'). RE: ademas las componentes de las otras
capas que no quedan alcanzadas por una acometida de fibra del mismo nodo (capa 'acometida_re').
"""
import argparse
import csv
import json
from pathlib import Path

from src.db import conectar

RAIZ = Path(__file__).resolve().parent.parent
TOPOLOGIA = "SELECT pgr_createTopology('red_noded', 0.0001, 'the_geom', 'id', 'source', 'target', clean := true)"

CREAR = """
DROP TABLE IF EXISTS nodos_clave CASCADE;
CREATE TABLE nodos_clave (
  id text PRIMARY KEY, nombre text, roles text, tipos text, localidad text, region text,
  lat double precision, lon double precision, coord_aproximada boolean, fuente text, url_fuente text,
  justificacion text, geom geometry(Point, 4326),
  vertice_id bigint, n_acometidas int, km_acometidas double precision,
  comp_rf int, comp_re int, cobertura text)"""

ACOMETIDAS = """
INSERT INTO red_noded (id, capa, sintetico, the_geom, largo_km)
WITH base AS (SELECT coalesce(max(id), 0) m FROM red_noded),
rf AS (
  SELECT DISTINCT ON (n.id, v.comp_rf) n.id nid, v.id vid, v.the_geom vgeom, n.geom ngeom, v.comp_re,
         'acometida'::text capa
  FROM nodos_clave n JOIN red_noded_vertices_pgr v
    ON v.comp_rf IS NOT NULL AND EXISTS (SELECT 1 FROM red_noded e WHERE e.capa = 'fibra' AND e.source = v.id OR e.capa = 'fibra' AND e.target = v.id)
   AND ST_DWithin(v.the_geom::geography, n.geom::geography, %(d)s)
  ORDER BY n.id, v.comp_rf, ST_Distance(v.the_geom::geography, n.geom::geography)
), re AS (
  SELECT DISTINCT ON (n.id, v.comp_re) n.id nid, v.id vid, v.the_geom vgeom, n.geom ngeom, v.comp_re,
         'acometida_re'::text capa
  FROM nodos_clave n JOIN red_noded_vertices_pgr v
    ON ST_DWithin(v.the_geom::geography, n.geom::geography, %(d)s)
  WHERE NOT EXISTS (SELECT 1 FROM rf WHERE rf.nid = n.id AND rf.comp_re = v.comp_re)
  ORDER BY n.id, v.comp_re, ST_Distance(v.the_geom::geography, n.geom::geography)
), todas AS (SELECT * FROM rf UNION ALL SELECT * FROM re),
lin AS (SELECT row_number() OVER (ORDER BY nid, capa, vid) rn, capa, ST_MakeLine(ngeom, vgeom) g FROM todas)
SELECT base.m + lin.rn, lin.capa, true, lin.g, ST_Length(lin.g::geography) / 1000
FROM lin, base WHERE ST_Length(lin.g) > 0 ORDER BY lin.rn"""

ACTUALIZAR = """
UPDATE nodos_clave n SET
  vertice_id = (SELECT v.id FROM red_noded_vertices_pgr v WHERE ST_DWithin(v.the_geom::geography, n.geom::geography, 50)
                ORDER BY ST_Distance(v.the_geom::geography, n.geom::geography) LIMIT 1);
UPDATE nodos_clave n SET
  comp_rf = v.comp_rf, comp_re = v.comp_re,
  n_acometidas = (SELECT count(*) FROM red_noded e WHERE e.capa LIKE 'acometida%%' AND (e.source = v.id OR e.target = v.id)),
  km_acometidas = (SELECT coalesce(sum(e.largo_km), 0) FROM red_noded e WHERE e.capa LIKE 'acometida%%' AND (e.source = v.id OR e.target = v.id))
FROM red_noded_vertices_pgr v WHERE v.id = n.vertice_id;
UPDATE nodos_clave SET cobertura = CASE
  WHEN vertice_id IS NULL THEN 'sin_cobertura'
  WHEN EXISTS (SELECT 1 FROM red_noded e WHERE e.capa = 'acometida' AND (e.source = vertice_id OR e.target = vertice_id)) THEN 'RF+RE'
  WHEN n_acometidas > 0 THEN 'solo_RE' ELSE 'sin_cobertura' END"""


def main(d_max):
    cfg = json.loads((RAIZ / "config.json").read_text())
    d_max = d_max or cfg["nodos_clave"]["d_max_acometida_m"]
    comp = (RAIZ / "sql" / "03_componentes.sql").read_text()
    with conectar(autocommit=True) as con:
        con.execute(CREAR)
        with open(RAIZ / "datos" / "nodos_clave.csv", encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                con.execute(
                    "INSERT INTO nodos_clave (id,nombre,roles,tipos,localidad,region,lat,lon,coord_aproximada,fuente,url_fuente,justificacion,geom) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,ST_SetSRID(ST_MakePoint(%s,%s),4326))",
                    (r["id"], r["nombre"], r["roles"], r["tipos"], r["localidad"], r["region"], float(r["lat"]),
                     float(r["lon"]), r["coord_aproximada"] == "true", r["fuente"], r["url_fuente"], r["justificacion"],
                     float(r["lon"]), float(r["lat"])))
        con.execute((RAIZ / "sql" / "02_red_noded.sql").read_text())  # red base, determinista, sin acometidas
        con.execute(comp)
        con.execute(ACOMETIDAS, {"d": d_max})
        con.execute(TOPOLOGIA)
        con.execute(comp)
        con.execute(ACTUALIZAR)
        for fila in con.execute("SELECT capa, count(*), round(sum(largo_km)::numeric,1) FROM red_noded WHERE capa LIKE 'acometida%' GROUP BY 1 ORDER BY 1"):
            print("acometidas", fila)
        n = con.execute("SELECT count(*) FROM nodos_clave WHERE vertice_id IS NULL").fetchone()[0]
        print(f"d_max={d_max} m; nodos sin vertice: {n}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dmax", type=float, help="distancia maxima de acometida en metros")
    main(ap.parse_args().dmax)
