from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from .asr import SherpaRecognizer
from .audio import PcmRecorder
from .codex_locator import CodexLocator
from .config import AppConfig
from .cues import AudioCuePlayer
from .gestures import GestureState, LongPressGesture
from .windows import is_foreground_codex, paste_text


class VoiceService:
    def __init__(
        self,
        config: AppConfig,
        model_dir: Path,
        *,
        locator: CodexLocator | None = None,
        recorder_factory: Callable[[], object] | None = None,
        recognizer_factory: Callable[[Path], object] | None = None,
        paste: Callable[[str, bool], bool] | None = None,
        target_active: Callable[[], bool] | None = None,
        notify: Callable[[str, str], None] | None = None,
        cue_start: Callable[[], None] | None = None,
        cue_stop: Callable[[], None] | None = None,
    ) -> None:
        self.config = config
        self.model_dir = Path(model_dir)
        self.locator = locator or CodexLocator()
        self._recorder_factory = recorder_factory or (
            lambda: PcmRecorder(
                sample_rate=config.sample_rate,
                max_seconds=config.max_record_seconds,
                device=config.input_device,
            )
        )
        self._recognizer_factory = recognizer_factory or (
            lambda path: SherpaRecognizer(
                path,
                threads=config.threads,
                sample_rate=config.sample_rate,
                noise_filter=config.noise_filter,
                vad_threshold=config.vad_threshold,
                min_voice_rms_dbfs=config.min_voice_rms_dbfs,
            )
        )
        self._target_active = target_active or is_foreground_codex
        self._paste = paste or self._default_paste
        self._notify = notify or (lambda status, message: None)
        cues = AudioCuePlayer(enabled=config.audio_cues)
        self._cue_start = cue_start or cues.play_start
        self._cue_stop = cue_stop or cues.play_stop
        self._lock = threading.RLock()
        self._recorder = None
        self._recognizer = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="codex-voice")
        self._mouse_listener = None
        self._hold_timer: threading.Timer | None = None
        self._max_timer: threading.Timer | None = None
        self._gesture: LongPressGesture | None = None
        self._paused = False
        self._started = False

    def _default_paste(self, text: str, target_active: bool) -> bool:
        return paste_text(
            text,
            target_active=target_active,
            restore_clipboard=self.config.restore_clipboard,
        )

    def begin_recording(self) -> bool:
        with self._lock:
            if self._recorder is not None:
                return False
            recorder = self._recorder_factory()
            try:
                recorder.start()
            except Exception as exc:
                self._notify("error", f"麦克风启动失败：{exc}")
                return False
            self._recorder = recorder
            if self._max_timer is not None:
                self._max_timer.cancel()
            self._max_timer = threading.Timer(
                max(1, self.config.max_record_seconds),
                self._auto_finish,
            )
            self._max_timer.daemon = True
            self._max_timer.start()
            self._cue_start()
            self._notify("recording", "正在听写，松开鼠标结束")
            return True

    def _auto_finish(self) -> None:
        if self._gesture is not None:
            self._gesture.cancel()
        else:
            self.finish_recording()

    def finish_recording(self) -> Future | None:
        with self._lock:
            recorder = self._recorder
            if recorder is None:
                return None
            self._recorder = None
            timer = self._max_timer
            self._max_timer = None
        if timer is not None:
            timer.cancel()
        try:
            pcm = recorder.stop()
        except Exception as exc:
            self._notify("error", f"停止录音失败：{exc}")
            return None
        self._cue_stop()
        self._notify("transcribing", "正在本地转写…")
        future = self._executor.submit(self._process_pcm, pcm)
        return future

    def _get_recognizer(self):
        with self._lock:
            if self._recognizer is None:
                self._recognizer = self._recognizer_factory(self.model_dir)
            return self._recognizer

    def _process_pcm(self, pcm: bytes) -> str:
        try:
            text = self._get_recognizer().transcribe_pcm16(pcm)
        except Exception as exc:
            self._notify("error", f"本地转写失败：{exc}")
            return ""
        if not text:
            self._notify("empty", "没有识别到语音")
            return ""
        target_active = self.config.auto_paste and self._target_active()
        try:
            injected = bool(self._paste(text, target_active))
        except Exception as exc:
            self._notify("error", f"文本粘贴失败：{exc}")
            return text
        self._notify("pasted" if injected else "copied", "已粘贴" if injected else "已复制，请手动粘贴")
        return text

    def pause(self) -> None:
        self._paused = True
        if self._gesture is not None:
            self._gesture.cancel()

    def resume(self) -> None:
        self._paused = False

    @property
    def paused(self) -> bool:
        return self._paused

    def _schedule_hold_tick(self) -> None:
        with self._lock:
            if self._hold_timer is not None:
                self._hold_timer.cancel()
            timer = threading.Timer(max(0.01, self.config.hold_ms / 1000.0 + 0.03), self._hold_tick)
            self._hold_timer = timer
            timer.daemon = True
            timer.start()

    def _hold_tick(self) -> None:
        with self._lock:
            self._hold_timer = None
            gesture = self._gesture
        if gesture is not None:
            gesture.tick()

    def _on_click(self, x, y, button, pressed) -> None:
        if self._paused:
            return
        try:
            from pynput.mouse import Button

            if button != Button.left:
                return
        except Exception:
            return
        gesture = self._gesture
        if gesture is None:
            return
        if pressed:
            gesture.press(int(x), int(y))
            if gesture.state is GestureState.PENDING:
                self._schedule_hold_tick()
        else:
            with self._lock:
                if self._hold_timer is not None:
                    self._hold_timer.cancel()
                    self._hold_timer = None
                if self._max_timer is not None:
                    self._max_timer.cancel()
                    self._max_timer = None
            gesture.release()

    def start(self) -> None:
        if self._started:
            return
        self._gesture = LongPressGesture(
            hit_test=self.locator.win32_hit_test,
            on_start=self.begin_recording,
            on_stop=lambda: self.finish_recording(),
            hold_ms=self.config.hold_ms,
        )
        from pynput import mouse

        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._mouse_listener.start()
        self._started = True
        self._notify("ready", "长按 Codex 输入框即可听写")

    def stop(self) -> None:
        if not self._started:
            return
        with self._lock:
            if self._hold_timer is not None:
                self._hold_timer.cancel()
                self._hold_timer = None
            if self._max_timer is not None:
                self._max_timer.cancel()
                self._max_timer = None
            recorder = self._recorder
            self._recorder = None
        if recorder is not None:
            recorder.cancel()
        if self._mouse_listener is not None:
            self._mouse_listener.stop()
            self._mouse_listener = None
        self.locator.close()
        self._executor.shutdown(wait=False, cancel_futures=True)
        self._started = False
