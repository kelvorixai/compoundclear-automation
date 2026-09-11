"""
Builds one episode's MP4 from its JSON spec.

Episode JSON shape (see content/episodes/ep01_compound-interest.json):
{
  "id": "ep01_compound-interest",
  "title": "...",
  "description": "...",
  "tags": ["..."],
  "privacy_status": "private",
  "segments": [
    {"id": 1, "text": "...", "slide": {"type": "statement"}},
    {"id": 2, "text": "...", "slide": {"type": "chart", "headline": "...", "sub": "...",
                                        "points": [[0,10000],[1,10700],...],
                                        "mark": [10, 19671.51], "y_max": 155000,
                                        "x_label": "Years", "y_label": "Value ($)"}},
    {"id": 3, "text": "...", "slide": {"type": "bars", "headline": "...",
                                        "labels": ["0-10","10-20"], "values": [9671, 19025]}},
    {"id": 4, "text": "...", "slide": {"type": "closing", "lines": ["The rate never changes.", "The base does."]}}
  ]
}

Usage: python build_video.py <episode.json> <output_dir>
Writes <output_dir>/<id>.mp4 and returns its path on stdout.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import slides as sl
from tts_piper import synth

LEAD_IN = 0.6
PAUSE = 0.4
END_HOLD = 1.2


def run(cmd):
    print("+", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        raise RuntimeError("cmd failed: " + " ".join(cmd))
    return r


def render_slide(spec, path):
    t = spec["type"]
    if t == "statement":
        sl.statement_slide(spec["_text"], path)
    elif t == "chart":
        sl.chart_slide(path, spec.get("headline", ""), spec.get("sub", ""),
                        spec["points"], spec.get("mark"), spec.get("y_max"),
                        spec.get("x_label", ""), spec.get("y_label", ""))
    elif t == "bars":
        sl.bars_slide(path, spec.get("headline", ""), spec["labels"], spec["values"],
                       spec.get("y_max"))
    elif t == "closing":
        sl.closing_slide(path, spec["lines"])
    else:
        raise ValueError(f"unknown slide type {t}")


def build(episode_path, out_dir):
    with open(episode_path) as f:
        ep = json.load(f)

    work = os.path.join(out_dir, ep["id"])
    os.makedirs(f"{work}/audio", exist_ok=True)
    os.makedirs(f"{work}/slides", exist_ok=True)

    durations = []
    for seg in ep["segments"]:
        wav_path = f"{work}/audio/seg{seg['id']}.wav"
        dur = synth(seg["text"], wav_path)
        seg["_dur"] = dur
        durations.append(dur)
        print(seg["id"], round(dur, 2), seg["text"][:50])

        slide_spec = dict(seg["slide"])
        slide_spec["_text"] = seg["text"]
        slide_path = f"{work}/slides/slide{seg['id']}.png"
        render_slide(slide_spec, slide_path)

    n = len(ep["segments"])

    # ---- silence padding ----
    def make_silence(path, dur):
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
             "-t", str(dur), "-c:a", "pcm_s16le", path])

    make_silence(f"{work}/audio/silence_lead.wav", LEAD_IN)
    make_silence(f"{work}/audio/silence_pause.wav", PAUSE)
    make_silence(f"{work}/audio/silence_end.wav", END_HOLD)

    with open(f"{work}/audio_list.txt", "w") as f:
        f.write(f"file 'audio/silence_lead.wav'\n")
        for i, seg in enumerate(ep["segments"], start=1):
            f.write(f"file 'audio/seg{seg['id']}.wav'\n")
            if i < n:
                f.write(f"file 'audio/silence_pause.wav'\n")
        f.write(f"file 'audio/silence_end.wav'\n")

    # run from within work dir so relative paths in the list files resolve
    cwd = os.getcwd()
    os.chdir(work)
    try:
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "audio_list.txt",
             "-c", "copy", "narration.wav"])

        img_durations = []
        for i, seg in enumerate(ep["segments"], start=1):
            gap = PAUSE if i < n else END_HOLD
            img_durations.append(seg["_dur"] + gap)
        img_durations[0] += LEAD_IN

        with open("images_list.txt", "w") as f:
            for i, seg in enumerate(ep["segments"], start=1):
                f.write(f"file 'slides/slide{seg['id']}.png'\n")
                f.write(f"duration {img_durations[i-1]:.3f}\n")
            f.write(f"file 'slides/slide{ep['segments'][-1]['id']}.png'\n")

        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "images_list.txt",
             "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-r", "30",
             "silent_video.mp4"])

        out_mp4 = f"{ep['id']}.mp4"
        run(["ffmpeg", "-y", "-i", "silent_video.mp4", "-i", "narration.wav",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", out_mp4])

        final_path = os.path.abspath(out_mp4)
    finally:
        os.chdir(cwd)

    return final_path


if __name__ == "__main__":
    episode_path, out_dir = sys.argv[1], sys.argv[2]
    path = build(episode_path, out_dir)
    print("BUILT:", path)
