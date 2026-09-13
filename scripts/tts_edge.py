"""
Neural TTS via Microsoft Edge's online voices (edge-tts).

Drop-in replacement for the old Piper module: exposes the same
`synth(text, out_path) -> duration_seconds` interface, so build_video.py
only needs its import line changed.

Free, no account, no API key. Needs network access, which the GitHub
Actions runner has. Piper was fully offline but sounds robotic; these are
Microsoft's neural voices and sound markedly more human.

Voice/rate/pitch are environment-overridable so they can be tuned without
touching code:
    TTS_VOICE  (default en-US-AndrewMultilingualNeural)
    TTS_RATE   (default -4%   — slightly slower reads as more deliberate)
    TTS_PITCH  (default +0Hz)
"""
import asyncio
import os
import subprocess
import tempfile
import wave

import edge_tts

VOICE = os.environ.get("TTS_VOICE", "en-US-AndrewMultilingualNeural")
RATE = os.environ.get("TTS_RATE", "-4%")
PITCH = os.environ.get("TTS_PITCH", "+0Hz")


async def _speak(text: str, mp3_path: str, voice: str) -> None:
    comm = edge_tts.Communicate(text, voice, rate=RATE, pitch=PITCH)
    await comm.save(mp3_path)


def synth(text: str, out_path: str, voice: str = None) -> float:
    """Synthesize `text` to a mono 22.05kHz WAV at `out_path`. Returns seconds."""
    voice = voice or VOICE
    fd, mp3 = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        asyncio.run(_speak(text, mp3, voice))
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", mp3,
             "-ar", "22050", "-ac", "1", out_path],
            check=True,
        )
    finally:
        if os.path.exists(mp3):
            os.remove(mp3)
    with wave.open(out_path, "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


if __name__ == "__main__":
    import sys
    print("duration:", synth(sys.argv[1], sys.argv[2]))
