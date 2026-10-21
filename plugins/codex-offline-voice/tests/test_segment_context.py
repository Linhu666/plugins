import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.speech_filter import expand_segment_with_context


class SegmentContextTests(unittest.TestCase):
    def test_expands_segment_with_pre_and_post_roll(self):
        samples = np.arange(1000, dtype=np.float32)
        expanded = expand_segment_with_context(samples, start=400, length=100, pre=100, post=50)
        self.assertEqual(expanded[0], 300.0)
        self.assertEqual(len(expanded), 250)


if __name__ == "__main__":
    unittest.main()
