"""Download or verify the seven source files without replacing historical checksums."""
import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def verificar(contenido, fuente):
    observed = (len(contenido), hashlib.sha256(contenido).hexdigest())
    accepted = [fuente] + fuente.get("variantes_verificadas", [])
    if not any(observed == (item["bytes"], item["sha256"]) for item in accepted):
        raise ValueError(
            "Checksum mismatch for {}: {} bytes, SHA-256 {}. "
            "The provider may have revised the source. The historical manifest and "
            "existing files are unchanged; obtain the recorded version before continuing."
            .format(fuente["archivo"], *observed)
        )


def descargar(fuente, raiz=RAIZ, offline=False):
    destino = (raiz / fuente["archivo"].replace("\\", "/")).resolve()
    if raiz.resolve() not in destino.parents:
        raise ValueError("Source path is outside the data directory")
    if destino.exists():
        verificar(destino.read_bytes(), fuente)
        return "verified existing file"
    if offline:
        raise FileNotFoundError("Missing source: {}".format(fuente["archivo"]))
    request = urllib.request.Request(fuente["url"], headers={"User-Agent": "replication-package/1.0"})
    with urllib.request.urlopen(request, timeout=300) as response:
        contenido = response.read()
    verificar(contenido, fuente)
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also prevents overwriting a file created during the download.
    with destino.open("xb") as output:
        output.write(contenido)
    return "downloaded and verified"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Verify local inputs without network access")
    args = parser.parse_args()
    fuentes = json.loads((RAIZ / "MANIFIESTO.json").read_text(encoding="utf-8"))
    failed = False
    for fuente in fuentes:
        try:
            print("{}: {}".format(fuente["nombre"], descargar(fuente, offline=args.verify_only)), flush=True)
        except Exception as error:
            print("{}: FAILED: {}".format(fuente["nombre"], error), file=sys.stderr, flush=True)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
