import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.__main__ import build_parser


class CliTests(unittest.TestCase):
    def test_no_tray_flag(self):
        args = build_parser().parse_args(["--no-tray"])
        self.assertTrue(args.no_tray)

    def test_diagnose_point_parses_coordinates(self):
        args = build_parser().parse_args(["--diagnose-point", "120,340"])
        self.assertEqual(args.diagnose_point, (120, 340))


if __name__ == "__main__":
    unittest.main()
