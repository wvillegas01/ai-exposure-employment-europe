"""Run the complete analysis in dependency order; stop at the first failure."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
STEPS = [
    "02_auditoria_datos/01_scripts/auditoria_datos.py",
    "03_crosswalk_soc_isco/01_scripts/crosswalk_aioe.py",
    "03_crosswalk_soc_isco/01_scripts/complementariedad.py",
    "03_crosswalk_soc_isco/01_scripts/validacion_isco1.py",
    "04_construccion_panel/01_scripts/construccion_panel.py",
    "03_crosswalk_soc_isco/01_scripts/exposicion_isco2.py",
    "09_robustez_multiindice/01_scripts/indices_isco2.py",
    "05_descriptivos_trayectorias/01_scripts/descriptivos.py",
    "06_tendencias_previas/01_scripts/tendencias_previas.py",
    "06_tendencias_previas/01_scripts/quiebre_pendiente.py",
    "07_did_intensidad_continua/01_scripts/tabla_principal.py",
    "08_sustitucion_complementariedad/01_scripts/sustitucion_complementariedad.py",
    "09_robustez_multiindice/01_scripts/multiindice.py",
    "10_heterogeneidad/01_scripts/heterogeneidad.py",
    "11_robustez/01_scripts/robustez.py",
    "11_robustez/01_scripts/robustez_expuestas.py",
    "12_amenazas_validez/01_scripts/placebo_anos_falsos.py",
    "16_revision_interna/01_scripts/inferencia_robusta.py",
    "16_revision_interna/01_scripts/equivalencia_y_2way.py",
    "16_revision_interna/01_scripts/nolinealidad_y_balanceado.py",
    "16_revision_interna/01_scripts/potencia_y_placebos.py",
    "16_revision_interna/01_scripts/regiones_y_robustez_detalle.py",
    "13_figuras_resultados/01_scripts/figuras.py",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Verify existing sources without downloading")
    parser.add_argument("--list", action="store_true", help="Print execution order without running")
    args = parser.parse_args()
    if args.list:
        print("01_datos_fuente/01_scripts/descarga_fuentes.py\n" + "\n".join(STEPS))
        return
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        env[key] = "1"
    source = [sys.executable, str(ROOT / "01_datos_fuente/01_scripts/descarga_fuentes.py")]
    if args.offline:
        source.append("--verify-only")
    subprocess.run(source, check=True, cwd=ROOT, env=env)
    for number, step in enumerate(STEPS, 1):
        print("[{}/{}] {}".format(number, len(STEPS), step), flush=True)
        subprocess.run([sys.executable, str(ROOT / step)], check=True, cwd=ROOT, env=env)


if __name__ == "__main__":
    main()
