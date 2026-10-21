import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.codex_locator import ControlInfo, is_codex_editable


class WholePageDocumentTests(unittest.TestCase):
    def test_rejects_whole_page_document_named_codex(self):
        info = ControlInfo("DocumentControl", "Codex", 42, "ChatGPT.exe", "Codex")
        self.assertFalse(is_codex_editable(info))


if __name__ == "__main__":
    unittest.main()
