from __future__ import annotations

import re
import wave
from pathlib import Path

import numpy as np

from .speech_filter import SpeechFilter


def clean_transcript(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()



def infer_model_kind(model_dir: Path) -> str:
    name = Path(model_dir).name.casefold()
    if "paraformer" in name:
        return "paraformer"
    if "sense-voice" in name or "sensevoice" in name:
        return "sensevoice"
    if "streaming" in name and "zipformer" in name:
        return "online_zipformer"
    if "zipformer" in name and "ctc" in name:
        return "offline_zipformer_ctc"
    return "online_zipformer"


class PcmBuffer:
    def __init__(self, max_bytes: int) -> None:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self._max_bytes = max_bytes
        self._data = bytearray()

    def append(self, data: bytes) -> None:
        if not data:
            return
        combined = bytes(self._data) + bytes(data)
        self._data = bytearray(combined[-self._max_bytes :])

    def value(self) -> bytes:
        return bytes(self._data)

    def clear(self) -> None:
        self._data.clear()


class SherpaRecognizer:
    def __init__(
        self,
        model_dir: Path,
        threads: int = 2,
        sample_rate: int = 16000,
        noise_filter: bool = True,
        vad_threshold: float = 0.45,
        min_voice_rms_dbfs: float = -50.0,
    ) -> None:
        self.model_dir = Path(model_dir)
        self.threads = max(1, int(threads))
        self.sample_rate = int(sample_rate)
        self.model_kind = infer_model_kind(self.model_dir)
        self._recognizer = None
        self._speech_filter = (
            SpeechFilter(
                self.model_dir,
                sample_rate=self.sample_rate,
                vad_threshold=vad_threshold,
                min_rms_dbfs=min_voice_rms_dbfs,
            )
            if noise_filter
            else None
        )

    @staticmethod
    def _find_model_files(model_dir: Path) -> tuple[Path, Path]:
        if not model_dir.exists():
            raise FileNotFoundError(f"Model directory not found: {model_dir}")
        models = sorted(model_dir.rglob("model.int8.onnx"))
        if not models:
            models = sorted(model_dir.rglob("model.onnx"))
        tokens = sorted(model_dir.rglob("tokens.txt"))
        if not models or not tokens:
            raise FileNotFoundError(
                f"Expected model.int8.onnx/model.onnx and tokens.txt under {model_dir}"
            )
        return models[0], tokens[0]

    def resolved_model_kind(self) -> str:
        model, _ = self._find_model_files(self.model_dir)
        return infer_model_kind(model.parent)

    @property
    def recognizer(self):
        if self._recognizer is None:
            import sherpa_onnx

            model, tokens = self._find_model_files(self.model_dir)
            self.model_kind = infer_model_kind(model.parent)
            common = {
                "tokens": str(tokens),
                "num_threads": self.threads,
                "sample_rate": self.sample_rate,
                "feature_dim": 80,
                "decoding_method": "greedy_search",
                "provider": "cpu",
            }
            if self.model_kind == "paraformer":
                self._recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
                    paraformer=str(model), **common
                )
            elif self.model_kind == "sensevoice":
                self._recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                    model=str(model), language="auto", use_itn=True, **common
                )
            elif self.model_kind == "offline_zipformer_ctc":
                self._recognizer = sherpa_onnx.OfflineRecognizer.from_zipformer_ctc(
                    model=str(model), **common
                )
            else:
                self._recognizer = sherpa_onnx.OnlineRecognizer.from_zipformer2_ctc(
                    model=str(model), **common
                )
        return self._recognizer

    def transcribe_pcm16(self, pcm: bytes, sample_rate: int | None = None) -> str:
        if len(pcm) < 2:
            return ""
        if self._speech_filter is not None:
            pcm = self._speech_filter.filter_pcm16(pcm)
            if len(pcm) < 2:
                return ""
        rate = int(sample_rate or self.sample_rate)
        usable = pcm[: len(pcm) - (len(pcm) % 2)]
        samples = np.frombuffer(usable, dtype="<i2").astype(np.float32) / 32768.0
        if samples.size == 0:
            return ""

        recognizer = self.recognizer
        stream = recognizer.create_stream()
        stream.accept_waveform(rate, samples)
        if self.model_kind == "online_zipformer":
            while recognizer.is_ready(stream):
                recognizer.decode_stream(stream)
            result = recognizer.get_result(stream)
            text = result if isinstance(result, str) else getattr(result, "text", "")
        else:
            recognizer.decode_stream(stream)
            text = stream.result.text
        return clean_transcript(text)

    def transcribe_wav(self, wav_path: Path) -> str:
        with wave.open(str(wav_path), "rb") as handle:
            if handle.getsampwidth() != 2:
                raise ValueError("Only 16-bit PCM WAV is supported")
            channels = handle.getnchannels()
            rate = handle.getframerate()
            samples = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2")
            if channels > 1:
                samples = samples.reshape(-1, channels).mean(axis=1).astype(np.int16)
            return self.transcribe_pcm16(samples.tobytes(), sample_rate=rate)
