"""Figuras del paper (PNG en figuras/). Lee la BD y config.json; sin valores escritos a mano."""
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np

from src.db import conectar

RAIZ = Path(__file__).resolve().parent.parent
FIG = RAIZ / "figuras"
AZUL, GRIS, TINTA = "#2F6DB5", "#8A8F98", "#222222"
plt.rcParams.update({"font.size": 8, "axes.edgecolor": GRIS, "axes.labelcolor": TINTA, "xtick.color": TINTA,
                     "ytick.color": TINTA, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": "#E3E5E8", "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "font.family": "serif"})
COMA = lambda v, d=0: f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def modelo_pga():
    m = json.loads((RAIZ / "config.json").read_text())["modelo"]
    h = 22.9
    with conectar() as con:
        h = con.execute("SELECT profundidad_km FROM sismo").fetchone()[0]
        nodos = {r[0]: r[1] for r in con.execute(
            "SELECT n.id, ST_Distance(n.geom::geography, s.geom::geography)/1000 FROM nodos_clave n, sismo s "
            "WHERE n.id IN ('N17','N15','N10')")}
    d = np.linspace(0, 700, 701)
    r = np.sqrt(d ** 2 + h ** 2)
    pga = m["A"] * np.exp(m["C"] * m["ms_max"]) / (r + m["D_km"]) ** m["B"]
    tasa = np.where(pga > m["alfa0_cms2"], m["Cp"] * m["Cd"] * m["Cg"] * m["c"] * np.maximum(pga - m["alfa0_cms2"], 0) ** m["b"], 0)
    fig, ax = plt.subplots(1, 2, figsize=(7.1, 2.3))
    for a, y, tit, u in ((ax[0], pga, "Aceleración máxima (línea gris: umbral de daño)", "cm/s²"), (ax[1], tasa, "Tasa de cortes", "cortes/km")):
        a.plot(d, y, color=AZUL, lw=1.6)
        a.set_xlabel("Distancia al epicentro (km)")
        a.set_ylabel(u)
        a.set_title(tit, fontsize=8, color=TINTA, loc="left")
        a.set_xlim(0, 700)
        a.set_ylim(0, None)
        for nid, nombre in (("N17", "Concepción"), ("N15", "Talca"), ("N10", "Santiago")):
            a.axvline(nodos[nid], color=GRIS, lw=0.8, ls=(0, (3, 2)))
            a.text(nodos[nid] + 6, a.get_ylim()[1] * 0.93, nombre, fontsize=7, color=TINTA, rotation=90, va="top")
    ax[0].axhline(m["alfa0_cms2"], color=GRIS, lw=0.8)
    fig.tight_layout()
    fig.savefig(FIG / "modelo_pga.png", dpi=300)
    plt.close(fig)


def hist_prob():
    rangos = [("0",), ("0–0,1",), ("0,1–0,5",), ("0,5–0,9",), ("0,9–1",)]
    lims = [(None, None), (0, 0.1), (0.1, 0.5), (0.5, 0.9), (0.9, 1.0)]
    with conectar() as con:
        km, n = [], []
        for i, (lo, hi) in enumerate(lims):
            if lo is None:
                q, p = "prob_falla = 0", ()
            else:
                q, p = "prob_falla > %s AND prob_falla <= %s", (lo, hi)
            f, k = con.execute(f"SELECT count(*), coalesce(sum(largo_km),0) FROM red_noded WHERE capa='fibra' AND {q}", p).fetchone()
            n.append(f)
            km.append(float(k))
    fig, ax = plt.subplots(figsize=(3.4, 2.3))
    x = np.arange(len(km))
    ax.bar(x, km, color=AZUL, width=0.62)
    for xi, k, f in zip(x, km, n):
        ax.text(xi, k + max(km) * 0.02, COMA(k), ha="center", fontsize=7, color=TINTA)
    ax.set_xticks(x, [r[0] for r in rangos])
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: COMA(v)))
    ax.set_xlabel("Probabilidad de falla del enlace")
    ax.set_ylabel("Fibra (km)")
    ax.set_ylim(0, max(km) * 1.15)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(FIG / "hist_prob.png", dpi=300)
    plt.close(fig)
    print("km por rango:", [round(k, 1) for k in km], "enlaces:", n)


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    modelo_pga()
    hist_prob()
