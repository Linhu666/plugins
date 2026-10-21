import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.codex_locator import ControlInfo, is_codex_editable


class UiaTypeNameTests(unittest.TestCase):
    def test_accepts_editcontrol_suffix(self):
        info = ControlInfo("EditControl", "随心输入", 42, "ChatGPT.exe", "ChatGPT")
        self.assertTrue(is_codex_editable(info))

    def test_accepts_documentcontrol_suffix(self):
        info = ControlInfo("DocumentControl", "Message", 42, "ChatGPT.exe", "Codex")
        self.assertTrue(is_codex_editable(info))


if __name__ == "__main__":
    unittest.main()
