from __future__ import annotations

import math
from pathlib import Path

import numpy as np


def high_pass_float(samples: np.ndarray, sample_rate: int, cutoff_hz: float = 80.0) -> np.ndarray:
    if samples.size == 0:
        return samples.astype(np.float32, copy=False)
    window = max(3, int(round(sample_rate / max(20.0, cutoff_hz))))
    if window % 2 == 0:
        window += 1
    pad = window // 2
    padded = np.pad(samples.astype(np.float32, copy=False), (pad, pad), mode="edge")
    cumulative = np.cumsum(padded, dtype=np.float64)
    cumulative = np.insert(cumulative, 0, 0.0)
    low = (cumulative[window:] - cumulative[:-window]) / window
    return (samples - low[: samples.size]).astype(np.float32)


def pcm16_to_float(pcm: bytes) -> np.ndarray:
    usable = pcm[: len(pcm) - (len(pcm) % 2)]
    return np.frombuffer(usable, dtype="<i2").astype(np.float32) / 32768.0


def float_to_pcm16(samples: np.ndarray) -> bytes:
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767.0).astype("<i2").tobytes()


def energy_gate_pcm16(
    pcm: bytes,
    sample_rate: int = 16000,
    min_rms_dbfs: float = -50.0,
) -> bytes:
    samples = pcm16_to_float(pcm)
    if samples.size == 0:
        return b""
    filtered = high_pass_float(samples, sample_rate)
    frame_size = max(1, int(sample_rate * 0.02))
    hop = max(1, int(sample_rate * 0.01))
    if filtered.size < frame_size:
        rms = float(np.sqrt(np.mean(np.square(filtered)) + 1e-12))
        db = 20.0 * math.log10(max(rms, 1e-8))
        return pcm if db >= min_rms_dbfs else b""

    starts = np.arange(0, filtered.size - frame_size + 1, hop)
    powers = np.array(
        [np.mean(np.square(filtered[start : start + frame_size])) for start in starts],
        dtype=np.float32,
    )
    db = 20.0 * np.log10(np.sqrt(powers + 1e-12) + 1e-8)
    keep = db >= min_rms_dbfs
    if not np.any(keep):
        return b""

    padding_frames = max(1, int(round(0.06 / 0.01)))
    expanded = keep.copy()
    for offset in range(1, padding_frames + 1):
        expanded[offset:] |= keep[:-offset]
        expanded[:-offset] |= keep[offset:]

    mask = np.zeros(filtered.size, dtype=bool)
    for start, active in zip(starts, expanded):
        if active:
            mask[start : min(start + frame_size + hop, filtered.size)] = True
    positions = np.flatnonzero(mask)
    if positions.size == 0:
        return b""
    output = np.zeros_like(filtered)
    output[mask] = filtered[mask]
    return float_to_pcm16(output[positions[0] : positions[-1] + 1])



def expand_segment_with_context(
    samples: np.ndarray,
    start: int,
    length: int,
    pre: int,
    post: int,
) -> np.ndarray:
    begin = max(0, int(start) - max(0, int(pre)))
    end = min(samples.size, int(start) + max(0, int(length)) + max(0, int(post)))
    return samples[begin:end]


class SpeechFilter:
    def __init__(
        self,
        model_dir: Path,
        sample_rate: int = 16000,
        vad_threshold: float = 0.45,
        min_rms_dbfs: float = -50.0,
    ) -> None:
        self.model_dir = Path(model_dir)
        self.sample_rate = int(sample_rate)
        self.vad_threshold = float(vad_threshold)
        self.min_rms_dbfs = float(min_rms_dbfs)
        self.vad_model = self._find_vad_model()

    def _find_vad_model(self) -> Path | None:
        if not self.model_dir.exists():
            return None
        for name in ("silero_vad.onnx", "silero_vad.int8.onnx"):
            matches = sorted(self.model_dir.rglob(name))
            if matches:
                return matches[0]
        return None

    def _vad_segments(self, samples: np.ndarray) -> list[tuple[int, np.ndarray]]:
        if self.vad_model is None:
            return []
        import sherpa_onnx

        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(self.vad_model)
        config.silero_vad.threshold = self.vad_threshold
        config.silero_vad.min_silence_duration = 0.35
        config.silero_vad.min_speech_duration = 0.20
        config.silero_vad.max_speech_duration = 30.0
        config.sample_rate = self.sample_rate
        config.num_threads = 1
        vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=60.0)
        segments: list[tuple[int, np.ndarray]] = []
        chunk_size = max(1, self.sample_rate // 10)
        for start in range(0, samples.size, chunk_size):
            vad.accept_waveform(samples[start : start + chunk_size])
            while not vad.empty():
                segment = vad.front
                segments.append((int(segment.start), np.asarray(segment.samples, dtype=np.float32)))
                vad.pop()
        vad.flush()
        while not vad.empty():
            segment = vad.front
            segments.append((int(segment.start), np.asarray(segment.samples, dtype=np.float32)))
            vad.pop()
        return segments

    def filter_pcm16(self, pcm: bytes) -> bytes:
        samples = pcm16_to_float(pcm)
        if samples.size == 0:
            return b""
        try:
            segments = self._vad_segments(samples)
        except Exception:
            return energy_gate_pcm16(pcm, self.sample_rate, self.min_rms_dbfs)
        if self.vad_model is not None:
            if not segments:
                return b""
            filtered: list[bytes] = []
            pre = int(self.sample_rate * 0.20)
            post = int(self.sample_rate * 0.12)
            for start, segment in segments:
                expanded = expand_segment_with_context(
                    samples,
                    start,
                    len(segment),
                    pre,
                    post,
                )
                segment_pcm = float_to_pcm16(expanded)
                gated = energy_gate_pcm16(segment_pcm, self.sample_rate, self.min_rms_dbfs)
                if gated:
                    filtered.append(gated)
            if not filtered:
                return b""
            silence = b"\x00\x00" * int(self.sample_rate * 0.08)
            return silence.join(filtered)
        return energy_gate_pcm16(pcm, self.sample_rate, self.min_rms_dbfs)
