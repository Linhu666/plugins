import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.config import AppConfig
from codex_voice.service import VoiceService


class FakeRecorder:
    def __init__(self):
        self.started = 0
        self.stopped = 0
        self.cancelled = 0

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1
        return b"pcm"

    def cancel(self):
        self.cancelled += 1


class FakeRecognizer:
    def __init__(self, text):
        self.text = text

    def transcribe_pcm16(self, pcm):
        return self.text


class ServiceTests(unittest.TestCase):
    def build_service(self, text="你好，Codex"):
        recorder = FakeRecorder()
        pasted = []
        statuses = []
        service = VoiceService(
            AppConfig(),
            model_dir=Path("model"),
            recorder_factory=lambda: recorder,
            recognizer_factory=lambda _: FakeRecognizer(text),
            paste=lambda value, target_active: pasted.append((value, target_active)) or True,
            target_active=lambda: True,
            notify=lambda status, message: statuses.append((status, message)),
        )
        return service, recorder, pasted, statuses

    def test_stop_transcribes_and_pastes_once(self):
        service, recorder, pasted, statuses = self.build_service()
        service.begin_recording()
        future = service.finish_recording()
        future.result(timeout=2)
        self.assertEqual(recorder.started, 1)
        self.assertEqual(recorder.stopped, 1)
        self.assertEqual(pasted, [("你好，Codex", True)])
        self.assertEqual([item[0] for item in statuses], ["recording", "transcribing", "pasted"])

    def test_empty_transcript_does_not_paste(self):
        service, _, pasted, statuses = self.build_service(text="")
        service.begin_recording()
        service.finish_recording().result(timeout=2)
        self.assertEqual(pasted, [])
        self.assertEqual(statuses[-1][0], "empty")

    def test_second_begin_is_ignored_while_recording(self):
        service, recorder, _, _ = self.build_service()
        service.begin_recording()
        service.begin_recording()
        self.assertEqual(recorder.started, 1)


if __name__ == "__main__":
    unittest.main()
