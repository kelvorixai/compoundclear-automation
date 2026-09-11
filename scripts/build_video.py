"""
Builds one episode's MP4 from its JSON spec.

Every episode automatically gets a branded intro (cold open) and outro
(subscribe CTA) prepended/appended around its own segments -- see
INTRO_TEXT/OUTRO_TEXT and slides.intro_slide/outro_slide below. Episode JSON
never needs to author these itself.

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
FPS = 30
ZOOM_RATE = 0.0015
ZOOM_MAX = 1.08

# Every episode gets the same branded cold open and subscribe CTA, so these
# live here (not in per-episode JSON) and apply automatically to all future
# episodes.
INTRO_TEXT = "CompoundClear."
OUTRO_TEXT = "If this was useful, subscribe to CompoundClear for more of the math behind money."


def run(cmd):
    print("+", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        raise RuntimeError("cmd failed: " + " ".join(cmd))
    return r


def render_slide_clip(image_path, duration, out_path, fps=FPS):
    """Renders a still slide as a short clip with a slow, subtle zoom-in
    (a "Ken Burns" effect) instead of a static freeze frame, so the video
    doesn't feel like a static slideshow. The zoom is capped low (1.08x) so
    it stays crisp on our flat vector-style slides without needing an
    expensive pre-upscale."""
    frames = max(1, round(duration * fps))
    vf = (f"zoompan=z='min(zoom+{ZOOM_RATE},{ZOOM_MAX})':d={frames}:s=1920x1080:fps={fps},"
          f"format=yuv420p")
    run(["ffmpeg", "-y", "-loop", "1", "-i", image_path,
         "-frames:v", str(frames), "-vf", vf, "-c:v", "libx264", "-r", str(fps),
         out_path])


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

    # Branded intro + the episode's own segments + branded outro. Every
    # episode gets this automatically -- no per-episode JSON authoring needed.
    all_segments = (
        [{"id": "intro", "text": INTRO_TEXT, "_kind": "intro"}]
        + [dict(seg, _kind="content") for seg in ep["segments"]]
        + [{"id": "outro", "text": OUTRO_TEXT, "_kind": "outro"}]
    )

    durations = []
    for seg in all_segments:
        wav_path = f"{work}/audio/seg{seg['id']}.wav"
        dur = synth(seg["text"], wav_path)
        seg["_dur"] = dur
        durations.append(dur)
        print(seg["id"], round(dur, 2), seg["text"][:50])

        slide_path = f"{work}/slides/slide{seg['id']}.png"
        if seg["_kind"] == "intro":
            sl.intro_slide(slide_path)
        elif seg["_kind"] == "outro":
            sl.outro_slide(slide_path)
        else:
            slide_spec = dict(seg["slide"])
            slide_spec["_text"] = seg["text"]
            render_slide(slide_spec, slide_path)

    n = len(all_segments)

    # ---- silence padding ----
    def make_silence(path, dur):
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
             "-t", str(dur), "-c:a", "pcm_s16le", path])

    make_silence(f"{work}/audio/silence_lead.wav", LEAD_IN)
    make_silence(f"{work}/audio/silence_pause.wav", PAUSE)
    make_silence(f"{work}/audio/silence_end.wav", END_HOLD)

    with open(f"{work}/audio_list.txt", "w") as f:
        f.write(f"file 'audio/silence_lead.wav'\n")
        for i, seg in enumerate(all_segments, start=1):
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
        for i, seg in enumerate(all_segments, start=1):
            gap = PAUSE if i < n else END_HOLD
            img_durations.append(seg["_dur"] + gap)
        img_durations[0] += LEAD_IN

        for i, seg in enumerate(all_segments, start=1):
            render_slide_clip(f"slides/slide{seg['id']}.png", img_durations[i - 1],
                               f"slides/clip{seg['id']}.mp4")

        with open("clips_list.txt", "w") as f:
            for seg in all_segments:
                f.write(f"file 'slides/clip{seg['id']}.mp4'\n")

        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "clips_list.txt",
             "-c", "copy", "silent_video.mp4"])

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
