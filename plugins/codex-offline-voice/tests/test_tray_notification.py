import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import codex_voice.tray as tray_module


class FakeIcon:
    def __init__(self, *args, **kwargs):
        self.title = ""
        self.icon = None
        self.notifications = []

    def notify(self, message, title):
        self.notifications.append((message, title))


class FakeService:
    paused = False


class TrayNotificationTests(unittest.TestCase):
    def test_status_update_does_not_show_system_notification(self):
        original = tray_module.pystray.Icon
        tray_module.pystray.Icon = FakeIcon
        try:
            tray = tray_module.TrayApp(FakeService())
            tray.notify("recording", "正在听写")
            self.assertEqual(tray.icon.notifications, [])
        finally:
            tray_module.pystray.Icon = original


if __name__ == "__main__":
    unittest.main()
