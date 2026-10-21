import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class InstallerWatchTests(unittest.TestCase):
    def test_startup_shortcut_uses_watch_codex(self):
        text = (ROOT / "scripts" / "install.ps1").read_text(encoding="utf-8")
        self.assertIn("--watch-codex", text)
        self.assertIn("$shortcut.Arguments", text)


if __name__ == "__main__":
    unittest.main()
