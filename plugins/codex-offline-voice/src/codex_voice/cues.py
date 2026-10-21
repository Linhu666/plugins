from __future__ import annotations

import io
import math
import struct
import threading
import wave

from typing import Iterable


def make_cue_wav(notes: Iterable[tuple[float, float]], sample_rate: int = 22050) -> bytes:
    frames = bytearray()
    for frequency, duration in notes:
        count = max(1, int(sample_rate * duration))
        fade = max(1, int(sample_rate * 0.006))
        for index in range(count):
            envelope = min(1.0, index / fade, (count - index - 1) / fade)
            value = int(0.32 * 32767 * math.sin(2 * math.pi * frequency * index / sample_rate) * envelope)
            frames.extend(struct.pack("<h", max(-32768, min(32767, value))))
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(frames))
    return output.getvalue()


class AudioCuePlayer:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._start = make_cue_wav([(659.25, 0.06), (987.77, 0.09)])
        self._stop = make_cue_wav([(783.99, 0.06), (523.25, 0.09)])

    def _play(self, data: bytes) -> None:
        if not self.enabled:
            return

        def worker() -> None:
            try:
                import winsound

                winsound.PlaySound(data, winsound.SND_MEMORY)
            except Exception:
                try:
                    import winsound

                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

        threading.Thread(target=worker, name="codex-voice-cue", daemon=True).start()

    def play_start(self) -> None:
        self._play(self._start)

    def play_stop(self) -> None:
        self._play(self._stop)
