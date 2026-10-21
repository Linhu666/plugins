import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.speech_filter import energy_gate_pcm16


class EnergyGateTests(unittest.TestCase):
    def test_removes_very_quiet_background_noise(self):
        rng = np.random.default_rng(42)
        noise = np.clip(rng.normal(0, 80, 16000), -32768, 32767).astype("<i2")
        filtered = energy_gate_pcm16(noise.tobytes(), sample_rate=16000, min_rms_dbfs=-45.0)
        self.assertEqual(filtered, b"")

    def test_keeps_clear_voice_level_signal(self):
        t = np.arange(16000, dtype=np.float32)
        tone = (3000 * np.sin(2 * np.pi * 440 * t / 16000)).astype("<i2")
        filtered = energy_gate_pcm16(tone.tobytes(), sample_rate=16000, min_rms_dbfs=-45.0)
        self.assertGreater(len(filtered), 0)


if __name__ == "__main__":
    unittest.main()
