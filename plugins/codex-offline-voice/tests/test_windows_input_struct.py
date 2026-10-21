import ctypes
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.windows import INPUT


class InputStructureTests(unittest.TestCase):
    def test_input_structure_matches_win64_abi(self):
        expected = 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28
        self.assertEqual(ctypes.sizeof(INPUT), expected)


if __name__ == "__main__":
    unittest.main()
