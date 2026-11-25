"""Analisis posterior al ATTR: nodos mas afectados y corredores criticos (puentes del grafo).

Corredor critico: conjunto de puentes (aristas cuya perdida desconecta el grafo) que separan los mismos
pares de nodos clave, es decir, tramos en serie. Impacto I = fraccion de los 276 pares que dejan de estar
conectados; probabilidad del corredor = 1 - prod(1 - p_e); riesgo = p_corredor * I.
"""
import csv
import json
from pathlib import Path

import networkx as nx
import numpy as np

from src.attr import etiquetas
from src.db import conectar

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "resultados"


def nodos_afectados():
    d = json.loads((RES / "attr.json").read_text())
    filas = []
    for nid, o in d["RE"]["operacion"]["conectividad_por_nodo"].items():
        f = {"id": nid, "nodo": o["nombre"]}
        for red in ("RF", "RE"):
            a = d[red]["operacion"]["conectividad_por_nodo"][nid]["conectividad_media"]
            b = d[red]["terremoto"]["conectividad_por_nodo"][nid]["conectividad_media"]
            f.update({f"antes_{red}": round(a, 4), f"despues_{red}": round(b, 4), f"caida_{red}": round(a - b, 4)})
        filas.append(f)
    filas.sort(key=lambda f: (-f["caida_RE"], -f["caida_RF"], f["id"]))
    with (RES / "08_nodos_afectados.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(filas)
    return filas


def corredores(red, cfg):
    capas = cfg["escenarios"][red]
    with conectar() as con:
        ar = con.execute("SELECT id, source, target, capa, largo_km, prob_falla, dist_epi_km FROM red_noded WHERE capa = ANY(%s) ORDER BY id", (capas,)).fetchall()
        nv = con.execute("SELECT max(id) FROM red_noded_vertices_pgr").fetchone()[0] + 1
        nodos = con.execute("SELECT id, nombre, vertice_id FROM nodos_clave ORDER BY id").fetchall()
    src = np.array([a[1] for a in ar]); dst = np.array([a[2] for a in ar])
    vert = np.array([n[2] for n in nodos]); K = len(nodos); total = K * (K - 1) / 2
    iu = np.triu_indices(K, 1)
    base = etiquetas(src, dst, np.ones(len(ar), dtype=bool), nv, vert)
    pares_base = (base[:, None] == base[None, :])[iu].sum()
    mult = {}
    for i, (_, s, t, *_r) in enumerate(ar):
        if s != t:
            mult.setdefault(frozenset((s, t)), []).append(i)
    G = nx.Graph()
    G.add_edges_from(tuple(k) for k in mult)
    grupos = {}
    for u, v in nx.bridges(G):
        idx = mult[frozenset((u, v))]
        if len(idx) != 1:
            continue
        i = idx[0]
        vivo = np.ones(len(ar), dtype=bool); vivo[i] = False
        lab = etiquetas(src, dst, vivo, nv, vert)
        pares = (lab[:, None] == lab[None, :])[iu].sum()
        if pares >= pares_base:
            continue
        comp = {}
        for k, l in enumerate(lab):
            comp.setdefault(int(l), []).append(nodos[k][0])
        firma = frozenset(frozenset(g) for g in comp.values() if len(g) > 1)
        grupos.setdefault(firma, {"I": (pares_base - pares) / total, "aristas": []})["aristas"].append(i)
    filas = []
    for firma, g in grupos.items():
        ps = [ar[i][5] for i in g["aristas"]]
        pc = 1 - float(np.prod([1 - p for p in ps]))
        km = sum(ar[i][4] for i in g["aristas"])
        # nodos del lado menor
        lados = sorted((sorted(x) for x in firma), key=len)
        filas.append({"red": red, "n_aristas": len(g["aristas"]), "km": round(km, 1), "capas": "+".join(sorted({ar[i][3] for i in g["aristas"]})),
                      "dist_epi_min_km": round(min(ar[i][6] for i in g["aristas"]), 1), "impacto": round(g["I"], 4),
                      "p_corredor": round(pc, 4), "riesgo": round(pc * g["I"], 4), "separa": " | ".join(",".join(x) for x in lados)})
    filas.sort(key=lambda f: (-f["riesgo"], -f["impacto"]))
    return filas, len(grupos)


def main():
    cfg = json.loads((RAIZ / "config.json").read_text())
    nodos = nodos_afectados()
    print("Nodos con mayor caida en RE:", [(f["id"], f["caida_RE"]) for f in nodos[:6]])
    todas = []
    for red in ("RF", "RE"):
        filas, n = corredores(red, cfg)
        print(f"[{red}] corredores con impacto > 0: {n}")
        for f in filas[:6]:
            print("   ", f)
        todas += filas
    with (RES / "08_enlaces_criticos.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(todas[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(todas)


if __name__ == "__main__":
    main()
