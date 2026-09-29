"""
Etapa 06 - Estudio de eventos y tendencias previas.

LA ETAPA QUE DECIDE. Si las ocupaciones expuestas ya divergian antes de 2023, lo que
se mida despues no es efecto de la IA generativa sino la continuacion de una tendencia.
Ese fue el error de la etapa 05 del articulo 1, y ahi el aviso lo dio la FIGURA, no los
p-valores: unos previos no significativos por falta de potencia se leyeron como
paralelismo. Aqui se reportan las tres cosas a la vez -coeficientes, contraste conjunto
y forma de la trayectoria- para que no vuelva a pasar.

Especificacion:
    y[o,c,t] = a[o,c] + g[c,t] + SUM_k b[k] * (exposicion[o] * 1{ano = k}) + e

Ano base: 2022, el ultimo previo al tratamiento. NO se usa 2021 como base porque es el
ano de la ruptura del reglamento IESS (etapa 02).

Errores estandar agrupados por OCUPACION: la exposicion solo varia entre las 40
ocupaciones, asi que ese es el nivel del tratamiento. Se reporta tambien el agrupamiento
por pais como alternativa.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyhdfe
from scipy import stats

RAIZ = Path(__file__).resolve().parents[1]
PANEL = RAIZ.parent / "04_construccion_panel" / "02_outputs" / "panel_analitico.csv"
SALIDA = RAIZ / "02_outputs"
SALIDA.mkdir(parents=True, exist_ok=True)

ANO_BASE = 2022
ANO_TRATAMIENTO = 2023


def ols_agrupado(y, X, grupos, k_absorbidos):
    """OLS con errores estandar agrupados y correccion de muestra pequena."""
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    e = y - X @ beta
    n, k = X.shape
    codigos = pd.factorize(grupos)[0]
    G = codigos.max() + 1
    meat = np.zeros((k, k))
    for g in range(G):
        m = codigos == g
        Xg, eg = X[m], e[m]
        s = Xg.T @ eg
        meat += np.outer(s, s)
    correccion = (G / (G - 1)) * ((n - 1) / (n - k - k_absorbidos))
    V = XtX_inv @ meat @ XtX_inv * correccion
    se = np.sqrt(np.diag(V))
    return beta, se, V, G


def estudio_evento(datos, dependiente):
    d = datos.dropna(subset=[dependiente]).copy()
    anos = sorted(a for a in d.ano.unique() if a != ANO_BASE)
    for a in anos:
        d[f"k_{a}"] = d.exposicion * (d.ano == a)
    columnas = [f"k_{a}" for a in anos]

    ids = np.column_stack([
        pd.factorize(d.geo + "_" + d.isco2)[0],
        pd.factorize(d.geo + "_" + d.ano.astype(str))[0],
    ])
    algoritmo = pyhdfe.create(ids, drop_singletons=False)
    residualizado = algoritmo.residualize(d[[dependiente] + columnas].to_numpy(dtype=float))
    y = residualizado[:, 0]
    X = residualizado[:, 1:]
    k_absorbidos = int(algoritmo.degrees)

    beta, se, V, G = ols_agrupado(y, X, d.isco2.to_numpy(), k_absorbidos)
    _, se_pais, _, G_pais = ols_agrupado(y, X, d.geo.to_numpy(), k_absorbidos)

    gl = G - 1
    tabla = pd.DataFrame({
        "ano": anos,
        "coef": beta,
        "se_ocupacion": se,
        "se_pais": se_pais,
        "t": beta / se,
        "p": 2 * (1 - stats.t.cdf(np.abs(beta / se), gl)),
    })
    tabla["ic_bajo"] = tabla.coef - stats.t.ppf(0.975, gl) * tabla.se_ocupacion
    tabla["ic_alto"] = tabla.coef + stats.t.ppf(0.975, gl) * tabla.se_ocupacion
    tabla["periodo"] = np.where(tabla.ano < ANO_TRATAMIENTO, "previo", "posterior")

    # Wald conjunto sobre los coeficientes previos
    idx = [i for i, a in enumerate(anos) if a < ANO_TRATAMIENTO]
    R = np.zeros((len(idx), len(anos)))
    for fila, i in enumerate(idx):
        R[fila, i] = 1.0
    Rb = R @ beta
    wald = float(Rb.T @ np.linalg.pinv(R @ V @ R.T) @ Rb / len(idx))
    p_wald = float(1 - stats.f.cdf(wald, len(idx), gl))

    return tabla, {
        "dependiente": dependiente,
        "n": int(len(d)),
        "efectos_absorbidos": k_absorbidos,
        "clusters_ocupacion": int(G),
        "clusters_pais": int(G_pais),
        "wald_previos_F": round(wald, 4),
        "wald_previos_p": round(p_wald, 4),
        "previos_significativos": int((tabla[tabla.periodo == "previo"].p < 0.05).sum()),
        "previos_totales": int((tabla.periodo == "previo").sum()),
        "posteriores_significativos": int((tabla[tabla.periodo == "posterior"].p < 0.05).sum()),
    }


def main():
    panel = pd.read_csv(PANEL)
    principal = panel[panel.muestra_principal == 1].copy()

    resultados = {}
    for dep in ("cuota", "log_empleo"):
        tabla, resumen = estudio_evento(principal, dep)
        tabla.to_csv(SALIDA / f"estudio_evento_{dep}.csv", index=False)
        resultados[dep] = resumen
        print(f"\n===== {dep} =====")
        print(json.dumps(resumen, indent=2, ensure_ascii=False))
        print(tabla[["ano", "periodo", "coef", "se_ocupacion", "p", "ic_bajo", "ic_alto"]]
              .to_string(index=False, float_format=lambda v: f"{v:9.5f}"))

    (SALIDA / "tendencias_previas.json").write_text(
        json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
