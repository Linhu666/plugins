import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.watcher import CodexWatcher


class FakeChild:
    def __init__(self):
        self.terminated = False
        self.waited = False
        self.exit_code = None

    def poll(self):
        return self.exit_code

    def terminate(self):
        self.terminated = True
        self.exit_code = 0

    def wait(self, timeout=None):
        self.waited = True
        return self.exit_code


class WatcherTests(unittest.TestCase):
    def test_starts_helper_when_codex_is_running(self):
        children = []
        watcher = CodexWatcher(
            is_codex_running=lambda: True,
            start_helper=lambda: children.append(FakeChild()) or children[-1],
        )
        watcher.tick()
        watcher.tick()
        self.assertEqual(len(children), 1)

    def test_stops_helper_when_codex_closes(self):
        state = [True]
        child = FakeChild()
        watcher = CodexWatcher(
            is_codex_running=lambda: state[0],
            start_helper=lambda: child,
        )
        watcher.tick()
        state[0] = False
        watcher.tick()
        self.assertTrue(child.terminated)
        self.assertTrue(child.waited)


if __name__ == "__main__":
    unittest.main()
