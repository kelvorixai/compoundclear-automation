"""
Render narration for the whole day's batch, one MP3 per line, and write
measured durations to samples/vo_batch.json so each animation can be cut
to the real voice timings.
"""
import asyncio
import json
import os
import subprocess

import edge_tts

VOICE = "en-US-AndrewMultilingualNeural"
RATE = "-4%"

SCRIPTS = {
    # LONG 2 — the three follow-ups
    "b2": [
        "What AI hands you first is a draft, not an answer.",
        "People who get great results out of it don't write better first prompts. They send better second ones.",
        "Follow up one. Cut this by forty percent without losing any of the points. "
        "A percentage is measurable. Make it shorter gets you a ten percent trim. "
        "Cut it by forty gets you a rewrite.",
        "Follow up two. Rewrite this so it sounds like a calm, senior person who is confident "
        "about the plan but not dismissive of the concern. Tone lands better as a description "
        "of a person than as a list of adjectives.",
        "Follow up three. Act as the most sceptical person on the receiving end. List the three "
        "objections they'd have, and tell me which one this draft doesn't answer. That turns the "
        "model from writer into reviewer, which is where it's most reliable.",
        "And when something's wrong, say what's wrong. Try again just gets you a random variation.",
    ],
    # LONG 3 — the context pack
    "b3": [
        "Ninety percent of the AI doesn't get it is missing context that never changes.",
        "Your role. Who reads your work. The words your company uses. How you write.",
        "So write it once. One block. Your job and your audience in two lines. The five acronyms "
        "your company says constantly. And three or four sentences you actually wrote, because a "
        "real sample does more for tone than any adjective you can think of.",
        "Then add the line that kills most invented facts. Don't invent numbers, names or dates. "
        "If you need one, write NEED, and I'll fill it in.",
        "Paste it at the top of anything that matters. In tools with memory, paste it once and it "
        "applies to everything after.",
        "One block, written once. Every prompt you send after it is better.",
    ],
    # SHORT 1 — percentages beat adjectives
    "s1": [
        "Stop telling AI to make it shorter. That gets you a ten percent trim. "
        "Say cut this by forty percent without losing any of the points. "
        "A percentage is measurable. An adjective isn't.",
    ],
    # SHORT 2 — the NEED rule
    "s2": [
        "AI will invent a number and sound completely certain about it. One line stops that. "
        "Add: don't invent numbers, names or dates, and if you need one, write NEED, "
        "and I'll fill it in.",
    ],
}

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "samples")


def dur(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return round(float(out.stdout.strip()), 3)


async def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    meta = {}
    for vid, lines in SCRIPTS.items():
        meta[vid] = []
        for i, text in enumerate(lines, 1):
            path = os.path.join(OUT_DIR, f"{vid}_l{i}.mp3")
            await edge_tts.Communicate(text, VOICE, rate=RATE).save(path)
            d = dur(path)
            meta[vid].append({"file": f"{vid}_l{i}.mp3", "sec": d, "text": text})
            print(f"{vid}_l{i}: {d}s")
        print(f"  -> {vid} total {round(sum(x['sec'] for x in meta[vid]),2)}s")
    with open(os.path.join(OUT_DIR, "vo_batch.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print("wrote vo_batch.json")


if __name__ == "__main__":
    asyncio.run(main())
