from __future__ import annotations

import threading
import time
from enum import Enum, auto
from typing import Callable


class GestureState(Enum):
    IDLE = auto()
    PENDING = auto()
    RECORDING = auto()


class LongPressGesture:
    """Single-pointer long-press state machine.

    The mouse listener calls press/release and a lightweight timer calls tick.
    Hit testing happens exactly once per qualifying button press.
    """

    def __init__(
        self,
        hit_test: Callable[[int, int], bool],
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        hold_ms: int = 350,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._hit_test = hit_test
        self._on_start = on_start
        self._on_stop = on_stop
        self._hold_s = max(0, hold_ms) / 1000.0
        self._clock = clock
        self._state = GestureState.IDLE
        self._pressed_at = 0.0
        self._lock = threading.RLock()

    @property
    def state(self) -> GestureState:
        with self._lock:
            return self._state

    def press(self, x: int, y: int) -> None:
        with self._lock:
            if self._state is not GestureState.IDLE:
                return
            if not self._hit_test(x, y):
                return
            self._pressed_at = self._clock()
            self._state = GestureState.PENDING

    def tick(self, now: float | None = None) -> None:
        with self._lock:
            if self._state is not GestureState.PENDING:
                return
            elapsed = (self._clock() if now is None else now) - self._pressed_at
            if elapsed < self._hold_s:
                return
            self._state = GestureState.RECORDING
            self._on_start()

    def release(self) -> None:
        with self._lock:
            if self._state is GestureState.PENDING:
                self._state = GestureState.IDLE
                return
            if self._state is GestureState.RECORDING:
                self._state = GestureState.IDLE
                self._on_stop()

    def cancel(self) -> None:
        with self._lock:
            was_recording = self._state is GestureState.RECORDING
            self._state = GestureState.IDLE
            if was_recording:
                self._on_stop()
