"""
Etapa 16d - Contraste formal de heterogeneidad regional y tabla completa de robustez.

Dos objeciones de la revision del 2026-09-25:

(a) Comparar p=0,002 en el este con p=0,769 en el oeste NO demuestra que los coeficientes
    difieran. Se estima un modelo CONJUNTO con interaccion exposicion x post x region sobre
    la submuestra expuesta y se contrasta la igualdad de coeficientes con un Wald, tanto el
    conjunto (las cuatro regiones iguales) como el especifico este-oeste.

(b) La tabla de robustez solo daba recuentos. Se genera la tabla completa con coeficiente,
    error estandar, valor p y n de cada una de las doce estimaciones, y se identifica cuales
    pierden significacion.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyhdfe
from scipy import stats

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "02_outputs"
sys.path.insert(0, str(RAIZ.parent / "11_robustez" / "01_scripts"))
sys.path.insert(0, str(RAIZ.parent / "06_tendencias_previas" / "01_scripts"))
from robustez import prepara, ajusta, panel as panel_bruto, VARIANTES_DEF  # noqa: E402
from tendencias_previas import ols_agrupado  # noqa: E402

REGIONES = {
    "Nordic": ["DK", "FI", "IS", "NO", "SE"],
    "Western": ["AT", "BE", "CH", "DE", "FR", "IE", "LU", "NL"],
    "Southern": ["CY", "EL", "ES", "IT", "MT", "PT"],
    "Eastern": ["BG", "CZ", "EE", "HR", "HU", "LT", "LV", "PL", "RO", "RS", "SI", "SK",
                "MK", "TR"],
}
panel = panel_bruto.drop(columns=["aioe_simple", "n_soc", "exposicion", "aioe_fraccional"],
                         errors="ignore")
ind = pd.read_csv(RAIZ.parent / "09_robustez_multiindice" / "02_outputs" / "indices_isco2.csv")
expo = ind[["isco2", "aioe", "theta"]]
expuestas = set(expo[expo.aioe > expo.aioe.median()].isco2)

# ------------------------------------------------ (a) modelo conjunto con interacciones
d = prepara(panel[panel.isco2.isin(expuestas)], expo).dropna(subset=["log_empleo"]).copy()
region_de = {g: r for r, gs in REGIONES.items() for g in gs}
d["region"] = d.geo.map(region_de)
assert d.region.notna().all(), sorted(d[d.region.isna()].geo.unique())

orden = ["Nordic", "Western", "Southern", "Eastern"]
cols = []
for r in orden:
    m = (d.region == r).astype(float)
    d[f"At_{r}"] = d.aioe_z * d.t * m
    d[f"Ap_{r}"] = d.aioe_z * d.post * m
    cols += [f"At_{r}", f"Ap_{r}"]
d["Tt"] = d.theta_z * d.t
d["Tp"] = d.theta_z * d.post
cols += ["Tt", "Tp"]

ids = np.column_stack([pd.factorize(d.geo + "_" + d.isco2)[0],
                       pd.factorize(d.geo + "_" + d.ano.astype(str))[0]])
alg = pyhdfe.create(ids, drop_singletons=False)
r_ = alg.residualize(d[["log_empleo"] + cols].to_numpy(dtype=float))
beta, se, V, G = ols_agrupado(r_[:, 0], r_[:, 1:], d.isco2.to_numpy(), int(alg.degrees))
gl = G - 1
idx = {c: i for i, c in enumerate(cols)}


def wald(R):
    Rb = R @ beta
    F = float(Rb.T @ np.linalg.pinv(R @ V @ R.T) @ Rb / R.shape[0])
    return round(F, 4), round(float(1 - stats.f.cdf(F, R.shape[0], gl)), 4)


# igualdad conjunta de los cuatro coeficientes regionales
R = np.zeros((3, len(cols)))
for f, r in enumerate(orden[1:]):
    R[f, idx[f"Ap_{orden[0]}"]] = 1.0
    R[f, idx[f"Ap_{r}"]] = -1.0
F_conj, p_conj = wald(R)

# contraste especifico este vs oeste
R2 = np.zeros((1, len(cols)))
R2[0, idx["Ap_Eastern"]] = 1.0
R2[0, idx["Ap_Western"]] = -1.0
F_ew, p_ew = wald(R2)

tc = stats.t.ppf(0.975, gl)
reg = []
for r in orden:
    i = idx[f"Ap_{r}"]
    reg.append({
        "region": r, "paises": len(REGIONES[r]),
        "coef": round(float(beta[i]), 6), "se": round(float(se[i]), 6),
        "ic_bajo": round(float(beta[i] - tc * se[i]), 6),
        "ic_alto": round(float(beta[i] + tc * se[i]), 6),
        "p": round(float(2 * (1 - stats.t.cdf(abs(beta[i] / se[i]), gl))), 4),
    })
pd.DataFrame(reg).to_csv(SALIDA / "regiones_conjunto.csv", index=False)

dif = float(beta[idx["Ap_Eastern"]] - beta[idx["Ap_Western"]])
se_dif = float(np.sqrt(R2 @ V @ R2.T))
salida = {"modelo_conjunto_regiones": reg,
          "wald_igualdad_cuatro_regiones": {"F": F_conj, "p": p_conj},
          "wald_este_vs_oeste": {"F": F_ew, "p": p_ew,
                                 "diferencia": round(dif, 6),
                                 "se_diferencia": round(se_dif, 6),
                                 "ic95": [round(dif - tc * se_dif, 6),
                                          round(dif + tc * se_dif, 6)]},
          "conglomerados_ocupacion": int(G)}
print("== modelo conjunto por region, log empleo, ocupaciones expuestas ==")
print(pd.DataFrame(reg).to_string(index=False))
print(f"\nWald igualdad de las cuatro regiones: F={F_conj}  p={p_conj}")
print(f"Wald este vs oeste: F={F_ew}  p={p_ew}  dif={dif:+.5f} "
      f"IC95 [{dif-tc*se_dif:+.5f}, {dif+tc*se_dif:+.5f}]")

# ------------------------------------------------ (b) robustez detallada
filas = []
for nombre, cfg in VARIANTES_DEF().items():
    p_ = cfg["panel"]
    for muestra, sel in (("exposed", p_[p_.isco2.isin(expuestas)]), ("all", p_)):
        dd = prepara(sel, cfg["expo"])
        for dep in ("cuota", "log_empleo"):
            res, Gv, n = ajusta(dd, dep, cfg.get("cluster", "isco2"))
            for term in ("aioe_post", "theta_post"):
                c, s_, p_v = res[term]
                filas.append({"variante": nombre, "muestra": muestra, "dependiente": dep,
                              "coeficiente": term, "estimacion": round(c, 6),
                              "se": round(s_, 6), "p": round(p_v, 4),
                              "n": int(n), "clusters": int(Gv)})
det = pd.DataFrame(filas)
det.to_csv(SALIDA / "robustez_detalle.csv", index=False)

print("\n== variantes que pierden significación para beta_A ==")
for dep in ("cuota", "log_empleo"):
    s = det[(det.coeficiente == "aioe_post") & (det.muestra == "exposed")
            & (det.dependiente == dep)]
    ns = s[s.p >= 0.05]
    print(f"  {dep}: {len(ns)} de {len(s)} -> "
          f"{[(r.variante, r.p) for r in ns.itertuples()] if len(ns) else 'ninguna'}")
salida["robustez_no_significativas"] = {
    dep: [[r.variante, r.p] for r in det[(det.coeficiente == "aioe_post")
          & (det.muestra == "exposed") & (det.dependiente == dep) & (det.p >= 0.05)].itertuples()]
    for dep in ("cuota", "log_empleo")}
(SALIDA / "regiones_y_robustez.json").write_text(
    json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
