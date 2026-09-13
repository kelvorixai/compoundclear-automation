"""
Render the same short script in several candidate voices so a human can
listen and pick one. Outputs MP3s into samples/ for easy playback straight
from GitHub's raw URLs.

Run:  python scripts/make_voice_samples.py
"""
import asyncio
import os

import edge_tts

SCRIPT = (
    "Most people use AI like a search box. One line in, one generic answer out, "
    "then twenty minutes fixing it. The fix is a five part prompt: role, context, "
    "task, format, and examples. Give the model whose expertise to borrow, what "
    "actually happened, one clear deliverable, the shape you want it in, and what "
    "to avoid. Brief it like a colleague, not a search box."
)

# The Multilingual voices are Microsoft's newest generation and the most natural.
VOICES = [
    ("andrew", "en-US-AndrewMultilingualNeural", "warm, conversational US male"),
    ("brian", "en-US-BrianMultilingualNeural", "relaxed, documentary US male"),
    ("ava", "en-US-AvaMultilingualNeural", "crisp, friendly US female"),
    ("ryan", "en-GB-RyanNeural", "measured British male"),
    ("sonia", "en-GB-SoniaNeural", "calm British female"),
]

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "samples")


async def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for slug, voice, desc in VOICES:
        path = os.path.join(OUT_DIR, f"{slug}.mp3")
        comm = edge_tts.Communicate(SCRIPT, voice, rate="-4%")
        await comm.save(path)
        print(f"wrote {path}  ({voice} - {desc})")


if __name__ == "__main__":
    asyncio.run(main())
