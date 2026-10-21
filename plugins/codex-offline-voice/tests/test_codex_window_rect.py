import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.codex_locator import CodexLocator


class TextChild:
    ControlTypeName = "TextControl"
    Name = "正在输入"
    ProcessId = 42
    def GetParentControl(self): return None
    class Rect:
        left=1000; top=1208; right=2000; bottom=1274
    BoundingRectangle=Rect()


class NullInitializer:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False


class WindowRectTests(unittest.TestCase):
    def test_uses_win32_window_rect_for_composer_region(self):
        locator = CodexLocator(
            inspector=lambda x, y: TextChild(),
            initializer_factory=lambda: NullInitializer(),
            process_name_resolver=lambda pid: "ChatGPT.exe",
            window_rect_provider=lambda x, y: (300, 100, 2300, 1360),
            retry_sleep=lambda _: None,
        )
        self.assertTrue(locator.hit_test(1500, 1265))
        locator.close()


if __name__ == "__main__":
    unittest.main()
