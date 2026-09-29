"""
Etapa 13 - Figuras finales.

Un solo script que RECALCULA lo que dibuja, para que las figuras no se desincronicen de
los datos. Etiquetas en ingles, narrativa en espanol (convencion del portafolio).
PNG + SVG + PDF a 300 ppp.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyhdfe
from scipy import stats

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "03_reports" / "figures"
SALIDA.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(RAIZ.parent / "06_tendencias_previas" / "01_scripts"))
from tendencias_previas import ols_agrupado  # noqa: E402

plt.rcParams.update({
    "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
    "figure.dpi": 300, "savefig.bbox": "tight",
})
AZUL, NARANJA, GRIS = "#1f4e79", "#c1622a", "#7a7a7a"


def guardar(fig, nombre):
    for ext in ("png", "svg", "pdf"):
        fig.savefig(SALIDA / f"{nombre}.{ext}", dpi=300)
    plt.close(fig)
    print("->", nombre)


panel = pd.read_csv(RAIZ.parent / "04_construccion_panel" / "02_outputs" / "panel_analitico.csv")
panel = panel[panel.muestra_principal == 1]
ind = pd.read_csv(RAIZ.parent / "09_robustez_multiindice" / "02_outputs" / "indices_isco2.csv")
d = panel.drop(columns=["aioe_simple", "n_soc", "exposicion", "aioe_fraccional"], errors="ignore") \
         .merge(ind[["isco2", "aioe", "theta"]], on="isco2")

# ---------------------------------------------------------------- F1 trayectorias
q = pd.qcut(d.aioe.rank(method="dense"), 4, labels=["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"])
tray = d.assign(q=q).groupby(["q", "ano"], observed=True).empleo_miles.sum().unstack(0)
tray = tray / tray.loc[2011] * 100
fig, ax = plt.subplots(figsize=(6.2, 3.9))
colores = [GRIS, "#9bb7d4", "#5d87b5", AZUL]
for col, c in zip(tray.columns, colores):
    ax.plot(tray.index, tray[col], color=c, lw=1.9, label=col)
    ax.annotate(f"{tray[col].iloc[-1]:.0f}", (tray.index[-1], tray[col].iloc[-1]),
                xytext=(4, -3), textcoords="offset points", color=c, fontsize=8.5)
ax.axvline(2022.5, color=NARANJA, lw=1.1, ls="--")
ax.text(2022.65, 137, "Generative AI", color=NARANJA, fontsize=8.5)
ax.set_xlabel("Year"); ax.set_ylabel("Employment (2011 = 100)")
ax.set_title("Employment by quartile of AI occupational exposure", fontsize=10, loc="left")
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.set_xlim(2011, 2026.2)
guardar(fig, "fig1_trayectorias_por_cuartil")

# ------------------------------------------------- estudio de eventos (recalculado)
def evento(datos, variable, dep="cuota", base=2022):
    dd = datos.dropna(subset=[dep]).copy()
    ocup = dd.drop_duplicates("isco2")
    dd["z"] = (dd[variable] - ocup[variable].mean()) / ocup[variable].std()
    otra = "theta" if variable != "theta" else "aioe"
    dd["z2"] = (dd[otra] - ocup[otra].mean()) / ocup[otra].std()
    anos = sorted(a for a in dd.ano.unique() if a != base)
    cols = []
    for a in anos:
        dd[f"a_{a}"] = dd.z * (dd.ano == a)
        dd[f"b_{a}"] = dd.z2 * (dd.ano == a)
        cols += [f"a_{a}", f"b_{a}"]
    ids = np.column_stack([pd.factorize(dd.geo + "_" + dd.isco2)[0],
                           pd.factorize(dd.geo + "_" + dd.ano.astype(str))[0]])
    alg = pyhdfe.create(ids, drop_singletons=False)
    r = alg.residualize(dd[[dep] + cols].to_numpy(dtype=float))
    beta, se, _, G = ols_agrupado(r[:, 0], r[:, 1:], dd.isco2.to_numpy(), int(alg.degrees))
    tc = stats.t.ppf(0.975, G - 1)
    idx = [i for i, c in enumerate(cols) if c.startswith("a_")]
    return pd.DataFrame({"ano": anos, "coef": beta[idx], "ic": tc * se[idx]})


e_aioe = evento(d, "aioe")
e_theta = evento(d, "theta")

fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7), sharey=True)
for ax, tab, titulo, color in ((axes[0], e_aioe, "AI exposure × year", AZUL),
                              (axes[1], e_theta, "Complementarity × year", NARANJA)):
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(2022.5, color=GRIS, lw=1.0, ls="--")
    sig = tab.coef.abs() > tab.ic
    ax.errorbar(tab.ano, tab.coef, yerr=tab.ic, fmt="none", ecolor=color, elinewidth=1.1, alpha=0.65)
    ax.scatter(tab.ano[~sig], tab.coef[~sig], facecolors="white", edgecolors=color, s=26, zorder=3, linewidths=1.2)
    ax.scatter(tab.ano[sig], tab.coef[sig], color=color, s=26, zorder=3)
    ax.set_title(titulo, fontsize=10, loc="left")
    ax.set_xlabel("Year")
axes[0].set_ylabel("Effect on employment share")
axes[0].text(2011.2, 0.0011, "10 of 11 pre-treatment\ncoefficients significant\n(Wald p = 0.0001)", fontsize=8, color=AZUL)
axes[1].text(2011.2, 0.0011, "0 of 11 significant\n(Wald p = 0.155)", fontsize=8, color=NARANJA)
fig.suptitle("Pre-trends: exposure is confounded with a secular trend, complementarity is not",
             fontsize=10.5, x=0.09, ha="left", y=1.03)
guardar(fig, "fig2_tendencias_previas")

# ---------------------------------------------------------------- F3 heterogeneidad
het = pd.read_csv(RAIZ.parent / "10_heterogeneidad" / "02_outputs" / "heterogeneidad_region.csv")
het = het[het.dependiente == "log_empleo"]
nombres = {"Nordicos": "Nordic (5)", "Occidental": "Western (8)",
           "Meridional": "Southern (6)", "Oriental y candidatos": "Eastern + candidates (14)"}
fig, ax = plt.subplots(figsize=(6.4, 3.2))
y = np.arange(len(het))
colores = [NARANJA if p < 0.05 else GRIS for p in het.p]
ax.barh(y, het.expo_post, color=colores, height=0.55)
ax.set_yticks(y); ax.set_yticklabels([nombres[r] for r in het.region])
ax.axvline(0, color="black", lw=0.8)
for i, (v, p) in enumerate(zip(het.expo_post, het.p)):
    ax.text(v + (0.0012 if v >= 0 else -0.0012), i, f"p = {p:.3f}",
            va="center", ha="left" if v >= 0 else "right", fontsize=8)
ax.set_xlabel("Exposure × post, log employment (exposed occupations)")
ax.set_title("The post-2022 acceleration is concentrated in Eastern Europe", fontsize=10, loc="left")
ax.set_xlim(-0.018, 0.052)
guardar(fig, "fig3_heterogeneidad_region")

# ---------------------------------------------------------------- F4 placebo
# v2 (2026-09-25): se anaden intervalos de confianza al 95 %, que la revision echaba en
# falta, y se separan visualmente los cortes falsos del real.
pl = pd.read_csv(RAIZ.parent / "16_revision_interna" / "02_outputs" / "placebo_con_ic.csv")
pl = pl[pl.dependiente == "log_empleo"].sort_values("corte").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(6.6, 3.6))
x = np.arange(len(pl))
es_real = (pl.tipo == "real").to_numpy()
for i in range(len(pl)):
    color = AZUL if es_real[i] else GRIS
    ax.plot([x[i], x[i]], [pl.ic_bajo[i], pl.ic_alto[i]], color=color, lw=1.6,
            solid_capstyle="round", zorder=2)
    ax.scatter(x[i], pl.aioe_post[i], s=46, zorder=3,
               color=color if es_real[i] else "white",
               edgecolors=color, linewidths=1.5)
ax.axhline(0, color="black", lw=0.8)
ax.axvline(len(pl) - 1.5, color=NARANJA, lw=1.0, ls="--")
ax.set_xticks(x)
ax.set_xticklabels([f"{c}\n{'actual' if r else 'placebo'}"
                    for c, r in zip(pl.corte, es_real)], fontsize=8.5)
for i in range(len(pl)):
    ax.annotate(f"p={pl.p[i]:.3f}", (x[i], pl.ic_alto[i]), xytext=(0, 5),
                textcoords="offset points", ha="center", fontsize=8,
                color=AZUL if es_real[i] else GRIS)
ax.set_ylabel("Exposure x post, log employment")
ax.set_title("Placebo cutoffs and the actual 2023 estimate, with 95% intervals",
             fontsize=10, loc="left")
ax.set_ylim(min(pl.ic_bajo) - 0.012, max(pl.ic_alto) + 0.016)
guardar(fig, "fig4_placebo")
print("figuras en", SALIDA)
