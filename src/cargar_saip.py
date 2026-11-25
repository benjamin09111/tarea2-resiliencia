"""Carga los 4 shapefiles SAIP (pyshp) en la tabla `red`. Idempotente."""
import json
from pathlib import Path

import shapefile

from src.db import conectar

RAIZ = Path(__file__).resolve().parent.parent


def main():
    cfg = json.loads((RAIZ / "config.json").read_text())
    carpeta = RAIZ / cfg["datos"]["carpeta_saip"]
    with conectar() as con:
        con.execute((RAIZ / "sql" / "00_esquema.sql").read_text())
        for nombre, meta in cfg["datos"]["capas"].items():
            sf = shapefile.Reader(str(carpeta / nombre))
            n_ok = n_desc = 0
            for sr in sf.shapeRecords():
                partes = sr.shape.parts
                pts = sr.shape.points
                if len(pts) < 2:
                    n_desc += 1
                    continue
                # una fila por parte (MultiLineString -> varias LineString)
                lim = list(partes) + [len(pts)]
                for a, b in zip(lim[:-1], lim[1:]):
                    seg = pts[a:b]
                    if len(seg) < 2:
                        n_desc += 1
                        continue
                    wkt = "LINESTRING(" + ",".join(f"{x:.9f} {y:.9f}" for x, y in seg) + ")"
                    con.execute(
                        "INSERT INTO red (capa, id_origen, sintetico, geom) "
                        "SELECT %s, %s, %s, g FROM (SELECT ST_GeomFromText(%s, 4326) g) t "
                        "WHERE ST_Length(g) > 0",
                        (meta["capa"], str(sr.record[0]), meta["sintetico"], wkt),
                    )
                    n_ok += 1
            print(f"{nombre}: {n_ok} lineas cargadas, {n_desc} descartadas")
        con.commit()


if __name__ == "__main__":
    main()
