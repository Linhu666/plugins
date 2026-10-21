import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.audio import PcmRecorder, resample_pcm16


class FakeStream:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.started = False
        self.stopped = False
        self.closed = False
        self.callback = kwargs["callback"]

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True


class AudioTests(unittest.TestCase):
    def test_callback_accumulates_raw_pcm(self):
        streams = []
        recorder = PcmRecorder(stream_factory=lambda **kwargs: streams.append(FakeStream(**kwargs)) or streams[-1])
        recorder.start()
        streams[0].callback(b"\x01\x00\x02\x00", 2, None, None)
        self.assertEqual(recorder.stop(), b"\x01\x00\x02\x00")
        self.assertTrue(streams[0].stopped)
        self.assertTrue(streams[0].closed)

    def test_cancel_discards_audio(self):
        streams = []
        recorder = PcmRecorder(stream_factory=lambda **kwargs: streams.append(FakeStream(**kwargs)) or streams[-1])
        recorder.start()
        streams[0].callback(b"\x01\x00", 1, None, None)
        recorder.cancel()
        self.assertEqual(recorder.stop(), b"")

    def test_resample_48k_to_16k_reduces_sample_count(self):
        source = b"\x00\x00" * 4800
        output = resample_pcm16(source, source_rate=48000, target_rate=16000)
        self.assertEqual(len(output), 1600 * 2)

    def test_recorder_retries_default_device_sample_rate(self):
        streams = []
        attempts = []

        def factory(**kwargs):
            attempts.append(kwargs["samplerate"])
            if kwargs["samplerate"] == 16000:
                raise RuntimeError("invalid sample rate")
            stream = FakeStream(**kwargs)
            streams.append(stream)
            return stream

        recorder = PcmRecorder(
            sample_rate=16000,
            stream_factory=factory,
            device_query=lambda _: {"default_samplerate": 48000},
        )
        recorder.start()
        self.assertEqual(attempts, [16000, 48000])
        self.assertEqual(len(streams), 1)
        recorder.cancel()


if __name__ == "__main__":
    unittest.main()
