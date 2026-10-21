import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.asr import SherpaRecognizer


class ModelRootDetectionTests(unittest.TestCase):
    def test_detects_paraformer_below_generic_models_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "models"
            actual = root / "sherpa-onnx-paraformer-zh-small-2024-03-09"
            actual.mkdir(parents=True)
            (actual / "model.int8.onnx").write_bytes(b"x")
            (actual / "tokens.txt").write_text("a 1\n", encoding="utf-8")
            recognizer = SherpaRecognizer(root)
            self.assertEqual(recognizer.resolved_model_kind(), "paraformer")


if __name__ == "__main__":
    unittest.main()
