"""Barrido de tolerancia de pgr_createTopology (sobre copias; no toca red_noded)."""
import csv
import json
from pathlib import Path

from src.db import conectar

RAIZ = Path(__file__).resolve().parent.parent
COMP = ("SELECT count(DISTINCT component) FROM pgr_connectedComponents("
        "'SELECT id, source, target, 1 AS cost, 1 AS reverse_cost FROM {t} WHERE capa = ANY(ARRAY[{capas}])')")


def barrido():
    cfg = json.loads((RAIZ / "config.json").read_text())
    filas = []
    with conectar(autocommit=True) as con:
        for tol in cfg["topologia"]["barrido_grados"]:
            con.execute("DROP TABLE IF EXISTS tmp_topo, tmp_topo_vertices_pgr CASCADE")
            con.execute("CREATE TABLE tmp_topo AS SELECT id, capa, the_geom, NULL::int source, NULL::int target FROM red_noded")
            con.execute("SELECT pgr_createTopology('tmp_topo', %s, 'the_geom', 'id', 'source', 'target', clean := true)", (tol,))
            nv = con.execute("SELECT count(*) FROM tmp_topo_vertices_pgr").fetchone()[0]
            rf = con.execute(COMP.format(t="tmp_topo", capas="''fibra''")).fetchone()[0]
            re = con.execute(COMP.format(t="tmp_topo", capas="''fibra'',''postacion'',''camino'',''ferry''")).fetchone()[0]
            # RF con topologia solo de fibra (descarta uniones inducidas por extremos de otras capas)
            con.execute("DROP TABLE IF EXISTS tmp_topo_f, tmp_topo_f_vertices_pgr CASCADE")
            con.execute("CREATE TABLE tmp_topo_f AS SELECT id, capa, the_geom, NULL::int source, NULL::int target FROM red_noded WHERE capa='fibra'")
            con.execute("SELECT pgr_createTopology('tmp_topo_f', %s, 'the_geom', 'id', 'source', 'target', clean := true)", (tol,))
            rf_sola = con.execute(COMP.format(t="tmp_topo_f", capas="''fibra''")).fetchone()[0]
            filas.append({"tolerancia_grados": tol, "tolerancia_m_aprox": round(tol * 111000, 1),
                          "vertices": nv, "componentes_RF": rf, "componentes_RF_solo_fibra": rf_sola,
                          "componentes_RE": re})
            print(filas[-1], flush=True)
        for t in ("tmp_topo", "tmp_topo_f"):
            con.execute(f"DROP TABLE IF EXISTS {t}, {t}_vertices_pgr CASCADE")
    out = RAIZ / "resultados" / "02_barrido_tolerancia.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(filas)
    print("escrito", out)


if __name__ == "__main__":
    barrido()
