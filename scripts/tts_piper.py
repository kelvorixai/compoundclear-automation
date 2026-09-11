"""
Local, offline neural TTS via Piper -- no account, no API key, no billing,
ever. Piper (https://github.com/OHF-Voice/piper1-gpl) is a fast, fully
local neural TTS engine that runs entirely on CPU inside the GitHub Actions
runner.

This module expects the voice model files to already be downloaded (the
GitHub Actions workflow downloads and caches them once -- see
.github/workflows/publish.yml). Default voice: en_US-lessac-high.
"""
import os
import wave

from piper import PiperVoice

MODEL_DIR = os.environ.get(
    "PIPER_MODEL_DIR", os.path.join(os.path.dirname(__file__), "..", "models")
)
MODEL_NAME = "en_US-lessac-high"
MODEL_PATH = os.path.join(MODEL_DIR, f"{MODEL_NAME}.onnx")
CONFIG_PATH = os.path.join(MODEL_DIR, f"{MODEL_NAME}.onnx.json")

_voice = None


def _get_voice():
    global _voice
    if _voice is None:
        _voice = PiperVoice.load(MODEL_PATH, config_path=CONFIG_PATH)
    return _voice


def synth(text: str, out_path: str) -> float:
    """Synthesize `text` to a WAV file at `out_path`. Returns duration in seconds."""
    voice = _get_voice()
    with wave.open(out_path, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    with wave.open(out_path, "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


if __name__ == "__main__":
    # quick smoke test: python tts_piper.py "hello world" out.wav
    import sys
    d = synth(sys.argv[1], sys.argv[2])
    print("duration:", d)
