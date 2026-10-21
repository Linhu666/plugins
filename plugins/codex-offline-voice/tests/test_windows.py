import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.windows import decode_clipboard_utf16, encode_clipboard_utf16, paste_text


class FakeClipboard:
    def __init__(self):
        self.value = "old"

    def get_text(self):
        return self.value

    def set_text(self, text):
        self.value = text


class FakeInput:
    def __init__(self):
        self.paste_count = 0

    def send_ctrl_v(self):
        self.paste_count += 1


class WindowsTests(unittest.TestCase):
    def test_utf16_clipboard_roundtrip_is_exact(self):
        raw = encode_clipboard_utf16("你好，Codex")
        self.assertEqual(decode_clipboard_utf16(raw), "你好，Codex")

    def test_inactive_target_only_copies_text(self):
        clipboard = FakeClipboard()
        keyboard = FakeInput()
        injected = paste_text(
            "新文本",
            target_active=False,
            clipboard=clipboard,
            input_backend=keyboard,
            restore_clipboard=True,
            sleep=lambda _: None,
        )
        self.assertFalse(injected)
        self.assertEqual(clipboard.value, "新文本")
        self.assertEqual(keyboard.paste_count, 0)

    def test_active_target_pastes_and_restores_old_text(self):
        clipboard = FakeClipboard()
        keyboard = FakeInput()
        injected = paste_text(
            "新文本",
            target_active=True,
            clipboard=clipboard,
            input_backend=keyboard,
            restore_clipboard=True,
            sleep=lambda _: None,
        )
        self.assertTrue(injected)
        self.assertEqual(keyboard.paste_count, 1)
        self.assertEqual(clipboard.value, "old")


if __name__ == "__main__":
    unittest.main()
