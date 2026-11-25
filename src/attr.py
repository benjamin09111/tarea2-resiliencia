"""ATTR (average two-terminal reliability) entre nodos clave, leyendo la topologia de la BD.

ATTR = (1 / C(K,2)) * sum_{i<j} Pr[s_i <-> s_j]    (Boettcher et al. 2018; Rai y Agrawal 1990)

- operacion: todas las aristas funcionan (p = 0), conectividad determinista -> valor exacto.
- terremoto: cada arista falla con su `prob_falla` de forma independiente; Monte Carlo con N
  realizaciones y semilla fija. ATTR = media de X_n (fraccion de pares conectados), EE = s/sqrt(N).
Escenarios de red (config.json): RF = fibra + acometida; RE = las cuatro capas + acometidas.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from src.db import conectar

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "resultados"


def cargar(red, cfg):
    capas = cfg["escenarios"][red]
    with conectar() as con:
        aristas = con.execute(
            "SELECT source, target, prob_falla FROM red_noded WHERE capa = ANY(%s) ORDER BY id", (capas,)
        ).fetchall()
        nv = con.execute("SELECT max(id) FROM red_noded_vertices_pgr").fetchone()[0]
        nodos = con.execute("SELECT id, nombre, vertice_id FROM nodos_clave ORDER BY id").fetchall()
    src = np.array([a[0] for a in aristas])
    dst = np.array([a[1] for a in aristas])
    p = np.array([a[2] for a in aristas], dtype=float)
    return src, dst, p, nv + 1, nodos


def etiquetas(src, dst, vivo, nv, vert):
    m = coo_matrix((np.ones(vivo.sum(), dtype=np.int8), (src[vivo], dst[vivo])), shape=(nv, nv))
    _, lab = connected_components(m, directed=False)
    out = lab[vert]
    # un nodo sin vertice queda aislado: etiqueta propia
    out = np.where(vert >= 0, out, -1 - np.arange(len(vert)))
    return out


def pares(lab):
    return lab[:, None] == lab[None, :]


def calcular(red, falla, cfg, n_iter=None, semilla=None):
    src, dst, p, nv, nodos = cargar(red, cfg)
    vert = np.array([n[2] if n[2] is not None else -1 for n in nodos])
    K = len(nodos)
    total = K * (K - 1) / 2
    iu = np.triu_indices(K, 1)
    if falla == "operacion":
        p = np.zeros_like(p)  # en operacion todos los enlaces funcionan: p_e = 0
        lab = etiquetas(src, dst, np.ones(len(src), dtype=bool), nv, vert)
        M = pares(lab).astype(float)
        attr, ee, n, conv = float(M[iu].sum() / total), 0.0, 1, []
        semilla = None
        metodo = "exacto (p = 0)"
    else:
        n = n_iter or cfg["attr"]["n_iter"]
        semilla = cfg["attr"]["semilla"] if semilla is None else semilla
        rng = np.random.default_rng(semilla)
        acum = np.zeros((K, K))
        xs = np.empty(n)
        conv = []
        for i in range(n):
            vivo = rng.random(len(src)) >= p
            M = pares(etiquetas(src, dst, vivo, nv, vert))
            acum += M
            xs[i] = M[iu].sum() / total
            if (i + 1) % 100 == 0:
                conv.append((i + 1, xs[: i + 1].mean()))
        M = acum / n
        attr = float(xs.mean())
        ee = float(xs.std(ddof=1) / np.sqrt(n))
        metodo = f"Monte Carlo, N = {n}, semilla {semilla}"
    por_nodo = {}
    for i, (nid, nombre, _) in enumerate(nodos):
        otros = np.arange(K) != i
        por_nodo[nid] = {"nombre": nombre, "conectividad_media": float(M[i][otros].mean())}
    grupos = {}
    if falla == "operacion":
        for i, (nid, nombre, _) in enumerate(nodos):
            grupos.setdefault(int(lab[i]), []).append(f"{nid} {nombre}")
    return {"red": red, "escenario_falla": falla, "metodo": metodo, "K": K, "pares": int(total),
            "n_aristas": int(len(src)), "n_aristas_p_positiva": int((p > 0).sum()),
            "attr": attr, "ee": ee, "ic95": [attr - 1.96 * ee, attr + 1.96 * ee], "n_iter": n, "semilla": semilla,
            "conectividad_por_nodo": por_nodo}, M, conv, grupos, nodos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--red", choices=["RF", "RE", "ambas"], default="ambas")
    ap.add_argument("--escenario-falla", choices=["operacion", "terremoto"], required=True)
    ap.add_argument("--n-iter", type=int)
    ap.add_argument("--semilla", type=int)
    ap.add_argument("--salida", default=str(RES / "attr.json"))
    a = ap.parse_args()
    cfg = json.loads((RAIZ / "config.json").read_text())
    salida = Path(a.salida)
    todo = json.loads(salida.read_text()) if salida.exists() else {}
    for red in (["RF", "RE"] if a.red == "ambas" else [a.red]):
        r, M, conv, grupos, nodos = calcular(red, a.escenario_falla, cfg, a.n_iter, a.semilla)
        todo.setdefault(red, {})[a.escenario_falla] = r
        print(f"[{red}] {a.escenario_falla}: ATTR = {r['attr']:.4f}  (EE {r['ee']:.4f}, IC95 {r['ic95'][0]:.4f}-{r['ic95'][1]:.4f})"
              f"  {r['metodo']}; K = {r['K']}, pares = {r['pares']}, aristas = {r['n_aristas']}, con p>0 = {r['n_aristas_p_positiva']}")
        if grupos:
            for g, miembros in sorted(grupos.items(), key=lambda kv: -len(kv[1])):
                print(f"    grupo de {len(miembros):2d}: " + "; ".join(miembros))
            with (RES / f"04_grupos_operacion_{red}.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(["grupo", "n_nodos", "nodos"])
                for k, (g, miembros) in enumerate(sorted(grupos.items(), key=lambda kv: -len(kv[1])), 1):
                    w.writerow([k, len(miembros), "; ".join(miembros)])
        if conv:
            with (RES / f"attr_convergencia_{red}.csv").open("w", newline="") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(["iteraciones", "attr_acumulado"])
                w.writerows(conv)
        if a.escenario_falla == "terremoto":
            ids = [n[0] for n in nodos]
            with (RES / f"attr_pares_{red}.csv").open("w", newline="") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow([""] + ids)
                for i, nid in enumerate(ids):
                    w.writerow([nid] + [f"{x:.4f}" for x in M[i]])
    salida.write_text(json.dumps(todo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
