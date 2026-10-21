import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.codex_locator import ControlInfo, is_codex_editable


class CodexLocatorTests(unittest.TestCase):
    def test_accepts_document_inside_chatgpt_shell(self):
        info = ControlInfo("Document", "Message Codex", 42, "ChatGPT.exe", "Codex")
        self.assertTrue(is_codex_editable(info))

    def test_accepts_edit_inside_codex_process_without_window_title(self):
        info = ControlInfo("Edit", "", 42, "codex.exe", "")
        self.assertTrue(is_codex_editable(info))

    def test_rejects_edit_inside_other_app(self):
        info = ControlInfo("Edit", "Search", 77, "notepad.exe", "Untitled - Notepad")
        self.assertFalse(is_codex_editable(info))

    def test_rejects_button_inside_codex(self):
        info = ControlInfo("Button", "Send", 42, "ChatGPT.exe", "Codex")
        self.assertFalse(is_codex_editable(info))


if __name__ == "__main__":
    unittest.main()
