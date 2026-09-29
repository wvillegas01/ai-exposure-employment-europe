"""
Etapa 11 - Robustez del contraste de la etapa 08.

Se somete el estimando principal (theta_post) y el indicio lateral (aioe_post) a doce
variantes. Cada fragilidad conocida del proyecto tiene aqui su variante: la ruptura de
2021, OC95, la regla de agregacion, las celdas de baja fiabilidad, la entrada tardia de
Serbia y la eleccion de conglomerado.

Lo que se busca no es que los numeros no se muevan -se moveran- sino si alguna
CONCLUSION cambia. En la etapa 11 del articulo 1 el signo dependia de la regla de
datacion y eso obligo a reescribir el enfoque; aqui hay que mirar lo mismo.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyhdfe
from scipy import stats

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ.parent / "01_datos_fuente"
PANEL = RAIZ.parent / "04_construccion_panel" / "02_outputs" / "panel_analitico.csv"
EXPO = RAIZ.parent / "03_crosswalk_soc_isco" / "02_outputs" / "exposicion_theta_isco2.csv"
SALIDA = RAIZ / "02_outputs"
SALIDA.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(RAIZ.parent / "06_tendencias_previas" / "01_scripts"))
from tendencias_previas import ols_agrupado  # noqa: E402

ANO_BASE, ANO_TRAT = 2022, 2023
COLS = ["aioe_t", "theta_t", "aioe_post", "theta_post"]


def prepara(panel, expo, col_aioe="aioe", col_theta="theta"):
    d = panel.merge(expo, on="isco2", how="left")
    ocup = d.drop_duplicates("isco2")
    d["aioe_z"] = (d[col_aioe] - ocup[col_aioe].mean()) / ocup[col_aioe].std()
    d["theta_z"] = (d[col_theta] - ocup[col_theta].mean()) / ocup[col_theta].std()
    d["t"] = d.ano - ANO_BASE
    d["post"] = (d.ano >= ANO_TRAT).astype(int)
    d["aioe_t"] = d.aioe_z * d.t
    d["theta_t"] = d.theta_z * d.t
    d["aioe_post"] = d.aioe_z * d.post
    d["theta_post"] = d.theta_z * d.post
    return d


def ajusta(d, dependiente, cluster="isco2"):
    d = d.dropna(subset=[dependiente] + COLS)
    ids = np.column_stack([
        pd.factorize(d.geo + "_" + d.isco2)[0],
        pd.factorize(d.geo + "_" + d.ano.astype(str))[0],
    ])
    alg = pyhdfe.create(ids, drop_singletons=False)
    r = alg.residualize(d[[dependiente] + COLS].to_numpy(dtype=float))
    beta, se, V, G = ols_agrupado(r[:, 0], r[:, 1:], d[cluster].to_numpy(), int(alg.degrees))
    gl = G - 1
    p = 2 * (1 - stats.t.cdf(np.abs(beta / se), gl))
    return {COLS[i]: (float(beta[i]), float(se[i]), float(p[i])) for i in range(len(COLS))}, int(G), int(len(d))


panel = pd.read_csv(PANEL)
panel = panel[panel.muestra_principal == 1]
expo = pd.read_csv(EXPO)[["isco2c", "aioe", "theta"]].rename(columns={"isco2c": "isco2"})

# --- variante de regla de agregacion: theta y aioe con media simple por SOC ---
theta_soc = pd.read_csv(RAIZ.parent / "03_crosswalk_soc_isco" / "02_outputs" / "theta_por_soc6.csv")
theta_soc["soc10"] = theta_soc.soc6.str.replace("-", "", regex=False).astype(int)
aioe_soc = pd.read_excel(FUENTE / "aioe" / "AIOE_DataAppendix.xlsx", sheet_name="Appendix A")
aioe_soc.columns = [str(c).strip() for c in aioe_soc.columns]
aioe_soc["soc10"] = aioe_soc["SOC Code"].astype(str).str.replace("-", "", regex=False).astype(int)
cw = pd.read_stata(FUENTE / "crosswalk" / "soc10_isco08.dta")
cw["isco2"] = "OC" + (cw.isco08 // 100).astype(int).astype(str).str.zfill(2)
simple = (aioe_soc.merge(theta_soc[["soc10", "theta"]], on="soc10").merge(cw, on="soc10")
          .groupby("isco2").agg(aioe=("AIOE", "mean"), theta=("theta", "mean")).reset_index())

def VARIANTES_DEF():
    return {
        "0_principal": dict(panel=panel, expo=expo),
        "1_sin_2021": dict(panel=panel[panel.ano != 2021], expo=expo),
        "2_previo_hasta_2020": dict(panel=panel[(panel.ano <= 2020) | (panel.ano >= 2023)], expo=expo),
        "3_sin_OC95": dict(panel=panel[panel.isco2 != "OC95"], expo=expo),
        "4_sin_OC25": dict(panel=panel[panel.isco2 != "OC25"], expo=expo),
        "5_regla_simple": dict(panel=panel, expo=simple),
        "6_sin_baja_fiabilidad": dict(panel=panel[~panel.baja_fiabilidad.astype(bool)], expo=expo),
        "7_solo_series_completas": dict(panel=panel[panel.geo != "RS"], expo=expo),
        "8_hasta_2024": dict(panel=panel[panel.ano <= 2024], expo=expo),
        "9_sin_Turquia": dict(panel=panel[panel.geo != "TR"], expo=expo),
        "10_sin_cinco_grandes": dict(panel=panel[~panel.geo.isin(["DE", "FR", "IT", "ES", "PL"])], expo=expo),
        "11_cluster_pais": dict(panel=panel, expo=expo, cluster="geo"),
    }


def main():
    VARIANTES = VARIANTES_DEF()
    filas = []
    for nombre, cfg in VARIANTES.items():
        d = prepara(cfg["panel"], cfg["expo"])
        for dep in ("cuota", "log_empleo"):
            res, G, n = ajusta(d, dep, cfg.get("cluster", "isco2"))
            filas.append({
                "variante": nombre, "dependiente": dep, "n": n, "clusters": G,
                "theta_post": round(res["theta_post"][0], 6),
                "theta_post_p": round(res["theta_post"][2], 4),
                "aioe_post": round(res["aioe_post"][0], 6),
                "aioe_post_p": round(res["aioe_post"][2], 4),
                "aioe_t": round(res["aioe_t"][0], 6),
                "aioe_t_p": round(res["aioe_t"][2], 4),
            })

    tabla = pd.DataFrame(filas)
    tabla.to_csv(SALIDA / "robustez.csv", index=False)

    resumen = {}
    for dep in ("cuota", "log_empleo"):
        s = tabla[tabla.dependiente == dep]
        resumen[dep] = {
            "theta_post_significativo_en": int((s.theta_post_p < 0.05).sum()),
            "theta_post_variantes": int(len(s)),
            "theta_post_rango": [round(float(s.theta_post.min()), 6), round(float(s.theta_post.max()), 6)],
            "theta_post_signo_positivo_en": int((s.theta_post > 0).sum()),
            "aioe_t_significativo_en": int((s.aioe_t_p < 0.05).sum()),
            "aioe_post_significativo_en": int((s.aioe_post_p < 0.05).sum()),
        }
    (SALIDA / "robustez_resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

    print(tabla.to_string(index=False))
    print("\n" + json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
