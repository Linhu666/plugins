import io
import sys
import unittest
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.cues import make_cue_wav


class CueWaveTests(unittest.TestCase):
    def test_generated_cue_is_valid_pcm_wav(self):
        data = make_cue_wav([(660, 0.06), (990, 0.09)], sample_rate=22050)
        self.assertTrue(data.startswith(b"RIFF"))
        with wave.open(io.BytesIO(data), "rb") as wav:
            self.assertEqual(wav.getnchannels(), 1)
            self.assertEqual(wav.getsampwidth(), 2)
            self.assertEqual(wav.getframerate(), 22050)
            self.assertAlmostEqual(wav.getnframes() / 22050, 0.15, places=2)


if __name__ == "__main__":
    unittest.main()
