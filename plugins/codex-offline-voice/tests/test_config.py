import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.config import AppConfig


class ConfigTests(unittest.TestCase):
    def test_missing_config_uses_defaults(self):
        with self.subTest("defaults"):
            import tempfile
            with tempfile.TemporaryDirectory() as directory:
                config = AppConfig.load(Path(directory) / "config.json")
                self.assertEqual(config.hold_ms, 200)
                self.assertEqual(config.sample_rate, 16000)
                self.assertEqual(config.threads, 2)
                self.assertTrue(config.audio_cues)
                self.assertTrue(config.noise_filter)

    def test_corrupt_config_is_backed_up(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "config.json"
            path.write_text("{bad", encoding="utf-8")
            config = AppConfig.load(path)
            self.assertEqual(config.hold_ms, 200)
            self.assertEqual(len(list(root.glob("config.corrupt-*.json"))), 1)

    def test_save_and_load_roundtrip(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            original = AppConfig(hold_ms=420, threads=1)
            original.save(path)
            loaded = AppConfig.load(path)
            self.assertEqual(loaded.hold_ms, 420)
            self.assertEqual(loaded.threads, 1)


if __name__ == "__main__":
    unittest.main()
