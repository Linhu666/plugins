import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.overlay import OverlayPresenter


class FakeOverlay:
    def __init__(self):
        self.calls = []

    def show(self, title, subtitle, color, duration=None):
        self.calls.append(("show", title, subtitle, color, duration))

    def hide(self):
        self.calls.append(("hide",))


class OverlayPresenterTests(unittest.TestCase):
    def test_recording_overlay_stays_visible(self):
        overlay = FakeOverlay()
        presenter = OverlayPresenter(overlay)
        presenter.notify("recording", "正在听写，松开鼠标结束")
        self.assertEqual(overlay.calls[0][0], "show")
        self.assertIsNone(overlay.calls[0][4])

    def test_transcribing_overlay_stays_visible(self):
        overlay = FakeOverlay()
        presenter = OverlayPresenter(overlay)
        presenter.notify("transcribing", "正在本地转写…")
        self.assertEqual(overlay.calls[0][0], "show")
        self.assertIsNone(overlay.calls[0][4])

    def test_success_overlay_hides_automatically(self):
        overlay = FakeOverlay()
        presenter = OverlayPresenter(overlay)
        presenter.notify("pasted", "已粘贴")
        self.assertEqual(overlay.calls[0][0], "show")
        self.assertEqual(overlay.calls[0][4], 1.2)

    def test_ready_hides_overlay(self):
        overlay = FakeOverlay()
        presenter = OverlayPresenter(overlay)
        presenter.notify("ready", "长按输入框")
        self.assertEqual(overlay.calls, [("hide",)])


if __name__ == "__main__":
    unittest.main()
