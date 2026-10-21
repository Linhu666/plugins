import os
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.asr import SherpaRecognizer


class SpeechFilterIntegrationTests(unittest.TestCase):
    def test_quiet_noise_never_loads_asr_model(self):
        rng = np.random.default_rng(7)
        quiet = np.clip(rng.normal(0, 70, 16000), -32768, 32767).astype("<i2")
        recognizer = SherpaRecognizer(Path("missing-model"))
        self.assertEqual(recognizer.transcribe_pcm16(quiet.tobytes()), "")

    @unittest.skipUnless(os.getenv("CODEX_VOICE_MODEL_DIR"), "model integration only")
    def test_vad_rejects_noise_only_audio(self):
        model_dir = Path(os.environ["CODEX_VOICE_MODEL_DIR"])
        rng = np.random.default_rng(11)
        noise = np.clip(rng.normal(0, 180, 32000), -32768, 32767).astype("<i2")
        recognizer = SherpaRecognizer(model_dir)
        self.assertEqual(recognizer.transcribe_pcm16(noise.tobytes()), "")

    @unittest.skipUnless(os.getenv("CODEX_VOICE_MODEL_DIR"), "model integration only")
    def test_vad_preserves_normal_speech(self):
        model_dir = Path(os.environ["CODEX_VOICE_MODEL_DIR"])
        fixture = Path(__file__).parent / "fixtures" / "zh_16k.wav"
        recognizer = SherpaRecognizer(model_dir)
        self.assertTrue(recognizer.transcribe_wav(fixture).strip())


if __name__ == "__main__":
    unittest.main()
