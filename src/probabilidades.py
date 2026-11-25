"""Aplica el modelo de falla (sql/04, sql/05) a cada enlace y actualiza la BD. Idempotente.

Opciones de sensibilidad (no cambian config.json): --ms, --cp, --acometidas-sin-falla.
"""
import argparse
import json
from pathlib import Path

from src.db import conectar

RAIZ = Path(__file__).resolve().parent.parent

FUENTES = {
    "A": "Saragoni, Astroza y Ruiz (2004), Tabla 1, ec. (2): interplaca, roca y suelo duro",
    "C": "Saragoni et al. (2004), Tabla 1, ec. (2)",
    "D_km": "Saragoni et al. (2004), Tabla 1, ec. (2)",
    "B": "Saragoni et al. (2004), Tabla 1, ec. (2)",
    "ms_max": "Ms de diseno chileno para sismos interplaca (Saragoni et al., 2004); Ms satura cerca de 8,5",
    "c": "Isoyama et al. (2000), ec. (5), curva estandar CIP",
    "b": "Isoyama et al. (2000), ec. (5)",
    "alfa0_cms2": "Isoyama et al. (2000): aceleracion desde la que ocurre dano",
    "Cp": "Isoyama et al. (2000), Tabla 3, factor de material (0,3 = hierro ductil; adoptado por analogia)",
    "Cd": "Isoyama et al. (2000), Tabla 3, factor de diametro (phi 75 mm)",
    "Cg": "Isoyama et al. (2000), Tabla 3, factor de topografia (aluvial, sin licuefaccion)",
    "largo_tramo_m": "discretizacion de cada enlace (Poisson no depende de la segmentacion)",
}


def aplicar(ms=None, cp=None, acometidas_sin_falla=False):
    """Escribe parametros y recalcula prob_falla de cada enlace. Devuelve el resumen impreso."""
    cfg = json.loads((RAIZ / "config.json").read_text())["modelo"]
    if ms is not None:
        cfg["ms_max"] = ms
    if cp is not None:
        cfg["Cp"] = cp
    sin_falla = list(cfg["capas_sin_falla"]) + (["acometida", "acometida_re"] if acometidas_sin_falla else [])
    with conectar(autocommit=True) as con:
        con.execute("DROP TABLE IF EXISTS parametros_modelo, parametros_capas CASCADE")
        con.execute("CREATE TABLE parametros_modelo (clave text PRIMARY KEY, valor double precision NOT NULL, fuente text)")
        for k, f in FUENTES.items():
            con.execute("INSERT INTO parametros_modelo VALUES (%s, %s, %s)", (k, float(cfg[k]), f))
        con.execute("CREATE TABLE parametros_capas (capa text PRIMARY KEY, expuesta boolean NOT NULL)")
        for capa in ("fibra", "postacion", "camino", "ferry", "acometida", "acometida_re"):
            con.execute("INSERT INTO parametros_capas VALUES (%s, %s)", (capa, capa not in sin_falla))
        con.execute((RAIZ / "sql" / "04_modelo_falla.sql").read_text())
        con.execute((RAIZ / "sql" / "05_probabilidades.sql").read_text())
        r = con.execute("SELECT count(*), count(*) FILTER (WHERE prob_falla > 0), min(prob_falla), max(prob_falla) FROM red_noded").fetchone()
    return f"enlaces: {r[0]}, con p>0: {r[1]}, p min {r[2]}, p max {r[3]:.6f}; sin falla: {sin_falla}; Ms max {cfg['ms_max']}, Cp {cfg['Cp']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ms", type=float, help="Ms maximo (por defecto config.json)")
    ap.add_argument("--cp", type=float, help="factor de material Cp")
    ap.add_argument("--acometidas-sin-falla", action="store_true", help="p = 0 en las acometidas sinteticas")
    a = ap.parse_args()
    print(aplicar(a.ms, a.cp, a.acometidas_sin_falla))


if __name__ == "__main__":
    main()
