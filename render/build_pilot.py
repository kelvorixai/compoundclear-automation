"""
Render the animated pilot inside GitHub Actions and mux Andrew's narration.

Frames come from render/engine.html, driven one frame at a time by headless
Chromium (?f=N renders the exact state at that frame). Narration MP3s are the
ones already committed under samples/. Outputs render/out/pilot.mp4 and
render/out/thumbnail.png, which upload_youtube.upload() then picks up.
"""
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")
FRAMES = os.path.join(OUT, "frames")
SAMPLES = os.path.join(ROOT, "samples")

FPS = 24
TOTAL_FRAMES = 1407          # 58.66s at 24fps
CHROME = os.environ.get("CHROME_BIN", "chromium-browser")

# (file, offset_ms) — measured from the real audio, animation was cut to these
VO = [
    ("vo_l1.mp3", 600), ("vo_l2.mp3", 3784), ("vo_l3.mp3", 8792),
    ("vo_l4.mp3", 29616), ("vo_l5.mp3", 40024), ("vo_l6.mp3", 53984),
]

FLAGS = [
    "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
    "--no-first-run", "--no-default-browser-check", "--disable-background-networking",
    "--disable-component-update", "--disable-client-side-phishing-detection",
    "--disable-sync", "--disable-default-apps", "--disable-extensions", "--no-pings",
    "--metrics-recording-only", "--disable-breakpad", "--disable-domain-reliability",
    "--host-resolver-rules=MAP * 0.0.0.0",
]


def shot(page: str, out_path: str, w: int, h: int, scale: int = 1) -> None:
    cmd = [CHROME] + FLAGS
    if scale != 1:
        cmd.append(f"--force-device-scale-factor={scale}")
    cmd += [f"--screenshot={out_path}", f"--window-size={w},{h}", page]
    subprocess.run(cmd, check=False, capture_output=True)


def render_frame(i: int) -> None:
    shot(f"file://{HERE}/engine.html?f={i}",
         os.path.join(FRAMES, f"{i:04d}.png"), 1920, 1080)


def main() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(FRAMES, exist_ok=True)

    print(f"rendering {TOTAL_FRAMES} frames...")
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as pool:
        list(pool.map(render_frame, range(TOTAL_FRAMES)))
    got = len(os.listdir(FRAMES))
    print(f"rendered {got} frames")
    if got < TOTAL_FRAMES:
        missing = [i for i in range(TOTAL_FRAMES)
                   if not os.path.exists(os.path.join(FRAMES, f"{i:04d}.png"))]
        print(f"retrying {len(missing)} missing frames")
        for i in missing:
            render_frame(i)

    # thumbnail (2x for crispness, then down to YouTube's 1280x720 spec)
    thumb_big = os.path.join(OUT, "thumb_2x.png")
    shot(f"file://{HERE}/thumbnail.html", thumb_big, 1280, 720, scale=2)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", thumb_big,
                    "-vf", "scale=1280:720", os.path.join(OUT, "thumbnail.png")],
                   check=True)

    # narration: lay each line at its measured offset, then normalise
    inputs, filters, labels = [], [], []
    for idx, (fname, ms) in enumerate(VO):
        inputs += ["-i", os.path.join(SAMPLES, fname)]
        filters.append(f"[{idx}:a]adelay={ms}|{ms}[a{idx}]")
        labels.append(f"[a{idx}]")
    dur = TOTAL_FRAMES / FPS
    fc = (";".join(filters) + ";" + "".join(labels)
          + f"amix=inputs={len(VO)}:duration=longest:normalize=0,"
            f"apad,atrim=0:{dur},loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    narration = os.path.join(OUT, "narration.m4a")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs
                   + ["-filter_complex", fc, "-map", "[out]",
                      "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "192k",
                      narration], check=True)

    video = os.path.join(OUT, "pilot.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                    "-framerate", str(FPS), "-i", os.path.join(FRAMES, "%04d.png"),
                    "-i", narration,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "17",
                    "-preset", "medium", "-profile:v", "high", "-level", "4.2",
                    "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", video], check=True)
    size = os.path.getsize(video)
    print(f"built {video} ({size/1e6:.1f} MB)")
    shutil.rmtree(FRAMES, ignore_errors=True)


if __name__ == "__main__":
    main()
