"""Contract tests: immutable inputs, offline checks and complete execution order."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("downloader", ROOT / "01_datos_fuente/01_scripts/descarga_fuentes.py")
downloader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(downloader)
spec2 = importlib.util.spec_from_file_location("runner", ROOT / "reproduce.py")
runner = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(runner)


class SourceContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = {"archivo": "data/input.csv", "bytes": 4,
                       "sha256": hashlib.sha256(b"good").hexdigest(), "url": "https://example.invalid/input"}

    def tearDown(self):
        self.tmp.cleanup()

    def test_existing_input_is_verified_without_network(self):
        target = self.root / self.source["archivo"]
        target.parent.mkdir()
        target.write_bytes(b"good")
        with patch.object(downloader.urllib.request, "urlopen", side_effect=AssertionError("Network used")):
            downloader.descargar(self.source, self.root)
        self.assertEqual(target.read_bytes(), b"good")

    def test_corrupted_input_is_not_overwritten(self):
        target = self.root / self.source["archivo"]
        target.parent.mkdir()
        target.write_bytes(b"bad")
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            downloader.descargar(self.source, self.root)
        self.assertEqual(target.read_bytes(), b"bad")

    def test_invalid_download_is_not_saved(self):
        with patch.object(downloader.urllib.request, "urlopen") as request:
            request.return_value.__enter__.return_value.read.return_value = b"changed"
            with self.assertRaises(ValueError):
                downloader.descargar(self.source, self.root)
        self.assertFalse((self.root / self.source["archivo"]).exists())

    def test_offline_missing_source_fails(self):
        with self.assertRaises(FileNotFoundError):
            downloader.descargar(self.source, self.root, offline=True)

    def test_only_explicit_equivalent_variant_is_accepted(self):
        self.source["variantes_verificadas"] = [{"bytes": 3, "sha256": hashlib.sha256(b"alt").hexdigest()}]
        downloader.verificar(b"alt", self.source)
        with self.assertRaises(ValueError):
            downloader.verificar(b"new", self.source)

    def test_runner_covers_every_analysis_script_once(self):
        expected = {p.relative_to(ROOT).as_posix() for p in ROOT.glob("*/01_scripts/*.py")
                    if not p.as_posix().endswith("descarga_fuentes.py")}
        self.assertEqual(set(runner.STEPS), expected)
        self.assertEqual(len(runner.STEPS), len(expected))


if __name__ == "__main__":
    unittest.main()
