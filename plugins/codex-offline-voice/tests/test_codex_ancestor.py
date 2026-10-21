import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.codex_locator import CodexLocator


class ParentDocument:
    ControlTypeName = "Document"
    Name = "Message Codex"
    ProcessId = 42

    def GetParentControl(self):
        return None


class ChildText:
    ControlTypeName = "TextControl"
    Name = "Hello"
    ProcessId = 42

    def GetParentControl(self):
        return ParentDocument()


class NullInitializer:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class AncestorHitTests(unittest.TestCase):
    def test_text_child_inside_editable_document_is_accepted(self):
        locator = CodexLocator(
            inspector=lambda x, y: ChildText(),
            initializer_factory=lambda: NullInitializer(),
            process_name_resolver=lambda pid: "ChatGPT.exe",
        )
        self.assertTrue(locator.hit_test(10, 20))


if __name__ == "__main__":
    unittest.main()
