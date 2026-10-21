import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.codex_locator import CodexLocator


class Group:
    ControlTypeName = "GroupControl"
    Name = ""
    ProcessId = 42

    def GetParentControl(self):
        return None


class Edit:
    ControlTypeName = "EditControl"
    Name = "随心输入"
    ProcessId = 42

    def GetParentControl(self):
        return None


class NullInitializer:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class LocatorRetryTests(unittest.TestCase):
    def test_hit_test_retries_transient_group_hit(self):
        controls = iter([Group(), Edit()])
        calls = []
        locator = CodexLocator(
            inspector=lambda x, y: calls.append((x, y)) or next(controls),
            initializer_factory=lambda: NullInitializer(),
            process_name_resolver=lambda pid: "ChatGPT.exe",
            retry_sleep=lambda _: None,
        )
        self.assertTrue(locator.hit_test(10, 20))
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
