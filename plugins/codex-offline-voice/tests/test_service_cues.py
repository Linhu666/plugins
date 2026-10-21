import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.config import AppConfig
from codex_voice.service import VoiceService


class FakeRecorder:
    def start(self): pass
    def stop(self): return b"pcm"
    def cancel(self): pass


class FakeRecognizer:
    def transcribe_pcm16(self, pcm): return "你好"


class CueServiceTests(unittest.TestCase):
    def test_service_emits_cue_before_each_phase(self):
        events = []
        service = VoiceService(
            AppConfig(),
            model_dir=Path("model"),
            recorder_factory=FakeRecorder,
            recognizer_factory=lambda _: FakeRecognizer(),
            paste=lambda text, active: True,
            target_active=lambda: True,
            notify=lambda status, message: events.append(status),
            cue_start=lambda: events.append("cue-start"),
            cue_stop=lambda: events.append("cue-stop"),
        )
        service.begin_recording()
        service.finish_recording().result(timeout=2)
        self.assertEqual(events, ["cue-start", "recording", "cue-stop", "transcribing", "pasted"])


if __name__ == "__main__":
    unittest.main()
