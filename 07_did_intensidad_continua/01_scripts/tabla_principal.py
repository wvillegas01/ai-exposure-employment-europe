"""Etapa 07 - Tabla principal de estimaciones (la que va al manuscrito)."""
import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ.parent / "11_robustez" / "01_scripts"))
from robustez import prepara, ajusta, panel as panel_bruto  # noqa: E402

SALIDA = RAIZ / "02_outputs"
SALIDA.mkdir(parents=True, exist_ok=True)
panel = panel_bruto.drop(columns=["aioe_simple", "n_soc", "exposicion", "aioe_fraccional"], errors="ignore")
ind = pd.read_csv(RAIZ.parent / "09_robustez_multiindice" / "02_outputs" / "indices_isco2.csv")
expo = ind[["isco2", "aioe", "theta"]]
expuestas = set(expo[expo.aioe > expo.aioe.median()].isco2)

filas = []
for muestra, p in (("Todas (40 ocupaciones)", panel),
                   ("Expuestas (20 ocupaciones)", panel[panel.isco2.isin(expuestas)])):
    d = prepara(p, expo)
    for dep, etiqueta in (("cuota", "Cuota de empleo"), ("log_empleo", "Log del empleo")):
        res, G, n = ajusta(d, dep)
        fila = {"muestra": muestra, "dependiente": etiqueta, "n": n, "conglomerados": G}
        for term, nombre in (("aioe_t", "Exposicion x tendencia"), ("theta_t", "Complementariedad x tendencia"),
                             ("aioe_post", "Exposicion x post"), ("theta_post", "Complementariedad x post")):
            c, se, pv = res[term]
            est = "***" if pv < 0.01 else "**" if pv < 0.05 else "*" if pv < 0.10 else ""
            fila[nombre] = f"{c:+.5f}{est}"
            fila[nombre + " (e.e.)"] = f"({se:.5f})"
        filas.append(fila)

t = pd.DataFrame(filas)
t.to_csv(SALIDA / "tabla_principal.csv", index=False)
print(t.to_string(index=False))
