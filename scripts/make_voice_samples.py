"""
Render the pilot narration, one MP3 per beat, and write the measured
durations to samples/vo_durations.json so the animation can be cut to the
voice rather than the voice squeezed into the animation.

Run:  python scripts/make_voice_samples.py
"""
import asyncio
import json
import os
import subprocess

import edge_tts

VOICE = "en-US-AndrewMultilingualNeural"
RATE = "-4%"

LINES = [
    ("l1", "Most people use AI like a search box."),
    ("l2", "One line in. One generic answer out. Then twenty minutes fixing it."),
    ("l3", "The fix is a five part prompt. Role: whose expertise to borrow. "
           "Context: what actually happened, and what's at stake. "
           "Task: one clear verb, one deliverable. "
           "Format: the length, structure and tone you want. "
           "And examples: a sample of the style, plus what to avoid."),
    ("l4", "Here's the same job briefed two ways. One line gets you a generic "
           "paragraph you'll rewrite anyway. The full brief gets you something "
           "you could send on the first pass."),
    ("l5", "In a Harvard and B C G study of seven hundred and fifty eight "
           "professionals, the ones using AI with proper guidance produced work "
           "rated forty percent higher, and did it twenty five percent faster."),
    ("l6", "Brief it like a colleague, not a search box."),
]

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "samples")


def duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    )
    return round(float(out.stdout.strip()), 3)


async def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    durations = {}
    for slug, text in LINES:
        path = os.path.join(OUT_DIR, f"vo_{slug}.mp3")
        await edge_tts.Communicate(text, VOICE, rate=RATE).save(path)
        durations[slug] = duration(path)
        print(f"{slug}: {durations[slug]}s  {text[:50]}...")
    meta = os.path.join(OUT_DIR, "vo_durations.json")
    with open(meta, "w") as f:
        json.dump({"voice": VOICE, "rate": RATE, "durations": durations}, f, indent=2)
    print("total:", round(sum(durations.values()), 2), "s")


if __name__ == "__main__":
    asyncio.run(main())
