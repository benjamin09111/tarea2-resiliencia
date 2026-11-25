"""Sensibilidad del ATTR a decisiones del modelo (no cambia los valores principales).

Casos: Ms = 8,8 (sin tope), Cp = 1,0 (material de la curva estandar), acometidas sin falla,
D_max = 10 y 30 km. Cada caso recalcula acometidas/probabilidades y el ATTR (operacion y terremoto)
y al final restituye el caso base, verificando que reproduce los valores principales.
"""
import json
from pathlib import Path

from src import nodos_clave, probabilidades
from src.attr import calcular
from src.db import conectar

RAIZ = Path(__file__).resolve().parent.parent
CASOS = [
    ("base", {}, None),
    ("Ms = 8,8", {"ms": 8.8}, None),
    ("Cp = 1,0", {"cp": 1.0}, None),
    ("acometidas sin falla", {"acometidas_sin_falla": True}, None),
    ("D_max = 10 km", {}, 10000),
    ("D_max = 30 km", {}, 30000),
]


def suma_p():
    with conectar() as con:
        return con.execute("SELECT count(*), sum(prob_falla), count(*) FILTER (WHERE capa LIKE 'acometida%') FROM red_noded").fetchone()


def main():
    cfg = json.loads((RAIZ / "config.json").read_text())
    base_dmax = cfg["nodos_clave"]["d_max_acometida_m"]
    salida = {}
    for nombre, kw, dmax in CASOS:
        nodos_clave.main(dmax or base_dmax)
        probabilidades.aplicar(**kw)
        fila = {"acometidas": suma_p()[2]}
        for red in ("RF", "RE"):
            op = calcular(red, "operacion", cfg)[0]
            te = calcular(red, "terremoto", cfg)[0]
            fila[red] = {"attr_operacion": op["attr"], "attr_terremoto": te["attr"], "ee": te["ee"],
                         "diferencia": te["attr"] - op["attr"],
                         "variacion_pct": 100 * (te["attr"] - op["attr"]) / op["attr"]}
        salida[nombre] = fila
        print(nombre, json.dumps({k: (round(v["attr_operacion"], 4), round(v["attr_terremoto"], 4)) if isinstance(v, dict) else v for k, v in fila.items()}), flush=True)
    # restituye el caso base y comprueba que es identico al de antes
    nodos_clave.main(base_dmax)
    probabilidades.aplicar()
    n_aristas, sp, n_ac = suma_p()
    for red in ("RF", "RE"):
        te = calcular(red, "terremoto", cfg)[0]["attr"]
        assert abs(te - salida["base"][red]["attr_terremoto"]) < 1e-12, "el caso base no se reprodujo"
    print(f"caso base restituido: {n_aristas} aristas, suma p = {sp:.6f}, acometidas = {n_ac}")
    (RAIZ / "resultados" / "attr_sensibilidad.json").write_text(json.dumps(salida, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
