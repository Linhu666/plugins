import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.gestures import GestureState, LongPressGesture


class LongPressGestureTests(unittest.TestCase):
    def test_short_click_does_not_start_recording(self):
        events = []
        gesture = LongPressGesture(
            hit_test=lambda x, y: True,
            on_start=lambda: events.append("start"),
            on_stop=lambda: events.append("stop"),
        )

        gesture.press(10, 20)
        gesture.release()

        self.assertEqual(events, [])
        self.assertEqual(gesture.state, GestureState.IDLE)

    def test_hold_inside_codex_starts_and_release_stops(self):
        now = [0.0]
        events = []
        gesture = LongPressGesture(
            hit_test=lambda x, y: True,
            on_start=lambda: events.append("start"),
            on_stop=lambda: events.append("stop"),
            clock=lambda: now[0],
        )

        gesture.press(10, 20)
        now[0] = 0.35
        gesture.tick()
        gesture.release()

        self.assertEqual(events, ["start", "stop"])
        self.assertEqual(gesture.state, GestureState.IDLE)

    def test_press_outside_codex_is_ignored(self):
        events = []
        gesture = LongPressGesture(
            hit_test=lambda x, y: False,
            on_start=lambda: events.append("start"),
            on_stop=lambda: events.append("stop"),
        )

        gesture.press(1, 2)
        gesture.tick(now=1.0)
        gesture.release()

        self.assertEqual(events, [])
        self.assertEqual(gesture.state, GestureState.IDLE)

    def test_second_press_while_recording_is_ignored(self):
        now = [0.0]
        events = []
        gesture = LongPressGesture(
            hit_test=lambda x, y: True,
            on_start=lambda: events.append("start"),
            on_stop=lambda: events.append("stop"),
            clock=lambda: now[0],
        )

        gesture.press(1, 2)
        now[0] = 1.0
        gesture.press(3, 4)
        gesture.tick()
        gesture.release()

        self.assertEqual(events, ["start", "stop"])


if __name__ == "__main__":
    unittest.main()
