import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.codex_locator import ControlInfo, is_codex_editable


class ComposerRegionTests(unittest.TestCase):
    def test_accepts_text_control_in_bottom_center_composer_region(self):
        info = ControlInfo(
            "TextControl",
            "正在输入",
            42,
            "ChatGPT.exe",
            "ChatGPT",
            rect=(1000, 1208, 2000, 1274),
            top_level_rect=(300, 100, 2300, 1360),
        )
        self.assertTrue(is_codex_editable(info))

    def test_rejects_text_control_in_message_area(self):
        info = ControlInfo(
            "TextControl",
            "历史消息",
            42,
            "ChatGPT.exe",
            "ChatGPT",
            rect=(1000, 500, 2000, 560),
            top_level_rect=(300, 100, 2300, 1360),
        )
        self.assertFalse(is_codex_editable(info))


if __name__ == "__main__":
    unittest.main()
