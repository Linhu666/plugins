import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.__main__ import build_parser


class WatchFlagTests(unittest.TestCase):
    def test_watch_codex_flag(self):
        args = build_parser().parse_args(["--watch-codex"])
        self.assertTrue(args.watch_codex)


if __name__ == "__main__":
    unittest.main()
