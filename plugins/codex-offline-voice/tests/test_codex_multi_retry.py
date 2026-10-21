import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.codex_locator import CodexLocator


class Group:
    ControlTypeName = "GroupControl"
    Name = ""
    ProcessId = 42
    def GetParentControl(self): return None
class Edit:
    ControlTypeName = "EditControl"
    Name = "随心输入"
    ProcessId = 42
    def GetParentControl(self): return None
class NullInitializer:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False


class MultiRetryTests(unittest.TestCase):
    def test_hit_test_recovers_after_two_transient_failures(self):
        controls = iter([Group(), Group(), Edit()])
        locator = CodexLocator(
            inspector=lambda x, y: next(controls),
            initializer_factory=lambda: NullInitializer(),
            process_name_resolver=lambda pid: "ChatGPT.exe",
            retry_sleep=lambda _: None,
        )
        self.assertTrue(locator.hit_test(10, 20))
        locator.close()


if __name__ == "__main__":
    unittest.main()
