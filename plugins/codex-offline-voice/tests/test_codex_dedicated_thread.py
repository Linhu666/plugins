import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.codex_locator import CodexLocator


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


class DedicatedThreadTests(unittest.TestCase):
    def test_hit_test_runs_in_dedicated_uia_thread(self):
        caller_thread = threading.get_ident()
        seen_threads = []
        locator = CodexLocator(
            inspector=lambda x, y: seen_threads.append(threading.get_ident()) or Edit(),
            initializer_factory=lambda: NullInitializer(),
            process_name_resolver=lambda pid: "ChatGPT.exe",
            retry_sleep=lambda _: None,
        )
        self.assertTrue(locator.hit_test(10, 20))
        self.assertNotEqual(seen_threads[0], caller_thread)
        locator.close()


if __name__ == "__main__":
    unittest.main()
