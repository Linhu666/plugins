import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.codex_locator import CodexLocator, ControlInfo, is_codex_editable


class FakeControl:
    ProcessId = 0
    ControlTypeName = "Document"
    Name = "Message"

    def GetParentControl(self):
        return None


class FakeInitializer:
    def __init__(self, events):
        self.events = events

    def __enter__(self):
        self.events.append("enter")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.events.append("exit")


class ThreadInitializationTests(unittest.TestCase):
    def test_inspect_point_initializes_uiautomation_for_current_thread(self):
        events = []
        locator = CodexLocator(
            inspector=lambda x, y: FakeControl(),
            initializer_factory=lambda: FakeInitializer(events),
        )
        locator.inspect_point(10, 20)
        locator.close()
        self.assertEqual(events, ["enter", "exit"])


if __name__ == "__main__":
    unittest.main()
