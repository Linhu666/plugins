import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.asr import infer_model_kind


class ModelKindTests(unittest.TestCase):
    def test_detects_paraformer_from_directory(self):
        self.assertEqual(infer_model_kind(Path("sherpa-onnx-paraformer-zh-small")), "paraformer")

    def test_detects_streaming_zipformer(self):
        self.assertEqual(infer_model_kind(Path("sherpa-onnx-streaming-zipformer-small-ctc-zh")), "online_zipformer")

    def test_detects_sensevoice(self):
        self.assertEqual(infer_model_kind(Path("sherpa-onnx-sense-voice-int8")), "sensevoice")


if __name__ == "__main__":
    unittest.main()
