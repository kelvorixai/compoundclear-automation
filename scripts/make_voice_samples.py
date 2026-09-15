"""
Render narration for the current batch, one MP3 per line, and write
measured durations to samples/vo_batch.json so each animation can be cut
to the real voice timings.

Only the videos listed in SCRIPTS are (re)rendered; earlier videos' MP3s in
samples/ are left untouched. Batch 1 (b2, b3, s1, s2) lives in git history.
"""
import asyncio
import json
import os
import subprocess

import edge_tts

VOICE = "en-US-AndrewMultilingualNeural"
RATE = "-4%"

SCRIPTS = {
    # LONG 4 — why AI flatters you, and the question that makes it honest
    "b4": [
        "Paste your draft into AI and ask, is this good? It says yes. Almost every time.",
        "That isn't your prompt. It's the training. These models learn from millions of human "
        "ratings, and people rate agreeable answers higher. In 2023, researchers at Anthropic "
        "tested five leading assistants. All five flattered the user, and raters sometimes "
        "picked a convincing yes over the correct answer.",
        "So the fix isn't a better draft. It's a question the model can't flatter its way out of.",
        "Rule one. Never ask a yes or no question about quality. Is this good, has a polite "
        "answer. What is the weakest sentence, and why, doesn't. It has to pick one.",
        "Rule two. Give it a reader with a reason to say no. Read this as the director who has "
        "thirty seconds and has already seen ten of these today. That reader is looking for a "
        "reason to stop.",
        "Rule three. Cap the praise. Score this out of ten, and nothing gets above a seven on a "
        "first draft. Now it has to spend the missing three points on real problems.",
        "Same draft. Same model. Ask for the weakest sentence instead of a compliment, and you "
        "get an editor instead of a fan.",
    ],
    # SHORT 3 — the weakest-sentence question
    "s3": [
        "Never ask AI, is this good? It learned from human ratings, and people rate a yes "
        "higher. Ask: what's the weakest sentence, and why? Now it has to pick one. "
        "An editor, not a fan.",
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
            print(f"{vid}_l{i}: {d}s", flush=True)
        print(f"  -> {vid} total {round(sum(x['sec'] for x in meta[vid]),2)}s", flush=True)
    with open(os.path.join(OUT_DIR, "vo_batch.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print("wrote vo_batch.json", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
