import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.codex_locator import CodexLocator


class NullInitializer:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False


class Win32HitTests(unittest.TestCase):
    def test_accepts_bottom_center_of_chatgpt_window(self):
        locator = CodexLocator(
            initializer_factory=lambda: NullInitializer(),
            window_info_provider=lambda x, y: ("ChatGPT.exe", (334, 125, 2265, 1358)),
        )
        self.assertTrue(locator.win32_hit_test(1500, 1265))
        locator.close()

    def test_rejects_middle_of_chatgpt_window(self):
        locator = CodexLocator(
            initializer_factory=lambda: NullInitializer(),
            window_info_provider=lambda x, y: ("ChatGPT.exe", (334, 125, 2265, 1358)),
        )
        self.assertFalse(locator.win32_hit_test(1500, 600))
        locator.close()

    def test_rejects_other_application(self):
        locator = CodexLocator(
            initializer_factory=lambda: NullInitializer(),
            window_info_provider=lambda x, y: ("notepad.exe", (334, 125, 2265, 1358)),
        )
        self.assertFalse(locator.win32_hit_test(1500, 1265))
        locator.close()


if __name__ == "__main__":
    unittest.main()
