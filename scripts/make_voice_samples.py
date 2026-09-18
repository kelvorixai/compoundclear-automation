"""
Render narration for the current batch, one MP3 per line, and write
measured durations to samples/vo_batch.json so each animation can be cut
to the real voice timings.

Only the videos listed in SCRIPTS are (re)rendered; earlier videos' MP3s in
samples/ are left untouched. Earlier batches live in git history.
"""
import asyncio
import json
import os
import subprocess

import edge_tts

VOICE = "en-US-AndrewMultilingualNeural"
RATE = "-4%"

SCRIPTS = {
    # LONG 5 — why AI misses the middle of a long paste (position effect)
    "b5": [
        "You paste a six page report, ask one question, and the answer quietly misses "
        "the thing on page three.",
        "This is a measured effect, not bad luck. In a 2023 study, researchers moved the "
        "same key fact to every position inside one long input. Accuracy was highest at "
        "the very beginning and at the very end. In the middle, it dropped.",
        "The curve is a U. Both ends are sharp. The middle sags. And a long document is "
        "mostly middle.",
        "So stop opening with your question. Paste the document first, then ask underneath "
        "it. The last thing it reads is your instruction, and that is the strongest "
        "position on the page.",
        "Better, say it twice. One line before the document telling it what to look for, "
        "and the same line after. Now your ask sits in both of the positions it reads best.",
        "And make the middle provable. Before it answers, ask it to quote the exact lines "
        "it used, word for word. If it can't quote them, it didn't read them.",
        "Same document. Same model. Same question. Move the question to the bottom, ask it "
        "to quote, and the middle stops disappearing.",
    ],
    # SHORT 4 — put the question after the document
    "s4": [
        "Your question goes after the document, not before it. Models read the start and "
        "the end best. The middle sags. So paste it, then ask underneath. The last line it "
        "reads is the one it follows.",
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
