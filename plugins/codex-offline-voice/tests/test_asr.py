import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from codex_voice.asr import PcmBuffer, SherpaRecognizer, clean_transcript


class AsrTests(unittest.TestCase):
    def test_clean_transcript_strips_outer_space(self):
        self.assertEqual(clean_transcript("  你好，Codex。 \n"), "你好，Codex。")

    def test_clean_transcript_collapses_repeated_blank_space(self):
        self.assertEqual(clean_transcript("你好   Codex\n\n请继续"), "你好 Codex 请继续")

    def test_pcm_limit_keeps_newest_audio(self):
        buffer = PcmBuffer(max_bytes=16)
        buffer.append(b"a" * 12)
        buffer.append(b"b" * 8)
        self.assertEqual(buffer.value(), b"a" * 8 + b"b" * 8)

    def test_empty_pcm_returns_empty_text_without_loading_model(self):
        recognizer = SherpaRecognizer(Path("missing-model"))
        self.assertEqual(recognizer.transcribe_pcm16(b""), "")

    @unittest.skipUnless(os.getenv("CODEX_VOICE_MODEL_DIR"), "model integration only")
    def test_model_transcribes_official_wav(self):
        model_dir = Path(os.environ["CODEX_VOICE_MODEL_DIR"])
        fixture = Path(__file__).parent / "fixtures" / "zh_16k.wav"
        recognizer = SherpaRecognizer(model_dir)
        self.assertTrue(recognizer.transcribe_wav(fixture).strip())


if __name__ == "__main__":
    unittest.main()
