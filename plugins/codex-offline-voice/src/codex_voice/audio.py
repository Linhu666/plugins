from __future__ import annotations

import threading
from typing import Callable, Mapping

import numpy as np

from .asr import PcmBuffer


def resample_pcm16(data: bytes, source_rate: int, target_rate: int) -> bytes:
    if not data or source_rate == target_rate:
        return data
    usable = data[: len(data) - (len(data) % 2)]
    source = np.frombuffer(usable, dtype="<i2").astype(np.float32)
    if source.size == 0:
        return b""
    target_size = max(1, int(round(source.size * target_rate / source_rate)))
    source_positions = np.arange(source.size, dtype=np.float64)
    target_positions = np.linspace(0, source.size - 1, target_size, dtype=np.float64)
    output = np.interp(target_positions, source_positions, source)
    return np.clip(output, -32768, 32767).astype("<i2").tobytes()


class PcmRecorder:
    def __init__(
        self,
        sample_rate: int = 16000,
        max_seconds: int = 60,
        device: int | str | None = None,
        stream_factory: Callable[..., object] | None = None,
        device_query: Callable[[int | str | None], Mapping] | None = None,
    ) -> None:
        self.sample_rate = int(sample_rate)
        self.max_seconds = max(1, int(max_seconds))
        self.device = device
        self._stream_factory = stream_factory
        self._device_query = device_query
        self._capture_rate = self.sample_rate
        self._buffer = PcmBuffer(self.sample_rate * 2 * self.max_seconds)
        self._stream = None
        self._lock = threading.RLock()

    def _make_stream(self, **kwargs):
        if self._stream_factory is not None:
            return self._stream_factory(**kwargs)
        import sounddevice as sd

        return sd.RawInputStream(**kwargs)

    def _query_device(self):
        if self._device_query is not None:
            return self._device_query(self.device)
        import sounddevice as sd

        return sd.query_devices(self.device, "input")

    def _open_started_stream(self, samplerate: int):
        stream = self._make_stream(
            samplerate=samplerate,
            channels=1,
            dtype="int16",
            blocksize=max(160, samplerate // 50),
            device=self.device,
            callback=self._callback,
        )
        try:
            stream.start()
            return stream
        except Exception:
            stream.close()
            raise

    def start(self) -> None:
        with self._lock:
            if self._stream is not None:
                return
            try:
                stream = self._open_started_stream(self.sample_rate)
                capture_rate = self.sample_rate
            except Exception as first_error:
                try:
                    fallback_rate = int(round(float(self._query_device()["default_samplerate"])))
                except Exception:
                    raise first_error
                if fallback_rate == self.sample_rate:
                    raise first_error
                stream = self._open_started_stream(fallback_rate)
                capture_rate = fallback_rate
            self._capture_rate = capture_rate
            self._buffer = PcmBuffer(capture_rate * 2 * self.max_seconds)
            self._stream = stream

    def _callback(self, indata, frames, time_info, status) -> None:
        with self._lock:
            self._buffer.append(bytes(indata))

    def _finish(self, keep_audio: bool) -> bytes:
        with self._lock:
            stream = self._stream
            self._stream = None
            capture_rate = self._capture_rate
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()
        with self._lock:
            result = self._buffer.value() if keep_audio else b""
            self._buffer.clear()
            self._capture_rate = self.sample_rate
        if result and capture_rate != self.sample_rate:
            return resample_pcm16(result, capture_rate, self.sample_rate)
        return result

    def stop(self) -> bytes:
        return self._finish(keep_audio=True)

    def cancel(self) -> None:
        self._finish(keep_audio=False)
