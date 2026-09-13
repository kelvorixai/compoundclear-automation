"""
Render any Kelvorix Digital video and upload it.

    python render/build2.py b2

Reads render/meta.json for the video's frame count, canvas size, narration
offsets and YouTube metadata. Frames come from render/engine2.html?v=<id>&f=<n>,
driven one frame at a time by headless Chrome. Writes render/out/<id>.mp4 plus
a thumbnail.png beside it, then upload_youtube.upload() picks both up.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SAMPLES = os.path.join(ROOT, "samples")
FPS = 24
CHROME = os.environ.get("CHROME_BIN", "google-chrome")

FLAGS = [
    "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
    "--no-first-run", "--no-default-browser-check", "--disable-background-networking",
    "--disable-component-update", "--disable-client-side-phishing-detection",
    "--disable-sync", "--disable-default-apps", "--disable-extensions", "--no-pings",
    "--metrics-recording-only", "--disable-breakpad", "--disable-domain-reliability",
    "--host-resolver-rules=MAP * 0.0.0.0",
]

_done = 0
_lock = threading.Lock()


def shot(page, out_path, w, h, scale=1):
    cmd = [CHROME] + FLAGS
    if scale != 1:
        cmd.append(f"--force-device-scale-factor={scale}")
    cmd += [f"--screenshot={out_path}", f"--window-size={w},{h}", page]
    try:
        subprocess.run(cmd, check=False, capture_output=True, timeout=90)
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT {out_path}", flush=True)


def main():
    vid = sys.argv[1]
    cfg = json.load(open(os.path.join(HERE, "meta.json")))[vid]
    total, (w, h) = cfg["frames"], cfg["size"]
    out = os.path.join(HERE, "out")
    frames = os.path.join(out, "frames")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(frames, exist_ok=True)

    def render_frame(i):
        global _done
        shot(f"file://{HERE}/engine2.html?v={vid}&f={i}",
             os.path.join(frames, f"{i:04d}.png"), w, h)
        with _lock:
            _done += 1
            if _done % 25 == 0 or _done == total:
                print(f"  {_done}/{total} frames", flush=True)

    print(f"rendering {vid}: {total} frames at {w}x{h} with {CHROME}", flush=True)
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as pool:
        list(pool.map(render_frame, range(total)))

    missing = [i for i in range(total)
               if not os.path.exists(os.path.join(frames, f"{i:04d}.png"))]
    if missing:
        print(f"retrying {len(missing)} frames", flush=True)
        for i in missing:
            render_frame(i)
        still = [i for i in range(total)
                 if not os.path.exists(os.path.join(frames, f"{i:04d}.png"))]
        if still:
            raise SystemExit(f"no output for {len(still)} frames (first {still[:5]}) "
                             f"- check CHROME_BIN={CHROME}")

    # thumbnail: reuse a representative frame's layout at 1280x720 for landscape;
    # for shorts YouTube uses the vertical frame itself, so grab an early frame.
    thumb_src = os.path.join(frames, f"{int(total*0.45):04d}.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", thumb_src,
                    "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,"
                           "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=#05080f",
                    os.path.join(out, "thumbnail.png")], check=True)

    # narration at measured offsets
    inputs, filters, labels = [], [], []
    for idx, (fname, ms) in enumerate(cfg["vo"]):
        inputs += ["-i", os.path.join(SAMPLES, fname)]
        filters.append(f"[{idx}:a]adelay={ms}|{ms}[a{idx}]")
        labels.append(f"[a{idx}]")
    dur = total / FPS
    fc = (";".join(filters) + ";" + "".join(labels)
          + f"amix=inputs={len(cfg['vo'])}:duration=longest:normalize=0,"
            f"apad,atrim=0:{dur},loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    narration = os.path.join(out, "narration.m4a")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs
                   + ["-filter_complex", fc, "-map", "[out]", "-ar", "48000",
                      "-ac", "2", "-c:a", "aac", "-b:a", "192k", narration], check=True)

    video = os.path.join(out, f"{vid}.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-framerate", str(FPS), "-i", os.path.join(frames, "%04d.png"),
                    "-i", narration,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17",
                    "-preset", "medium", "-profile:v", "high", "-level", "4.2",
                    "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", video], check=True)
    print(f"built {video} ({os.path.getsize(video)/1e6:.1f} MB)", flush=True)

    # episode-shaped metadata for upload_youtube.upload()
    with open(os.path.join(out, "meta.json"), "w") as f:
        json.dump(cfg["youtube"], f, indent=2)
    shutil.rmtree(frames, ignore_errors=True)


if __name__ == "__main__":
    main()
