"""
Top-level orchestrator run by the GitHub Actions workflow.

1. Finds the next episode JSON in content/episodes/ with status "ready"
   (falls back to no status field = ready, for hand-authored episodes).
2. Builds the video (TTS + slides + ffmpeg assembly).
3. Uploads it to YouTube as private.
4. Marks the episode "published" with the resulting video_id, so the next
   run picks the next one. The workflow commits this change back to git.

If no ready episode exists, exits cleanly (status 0) so the scheduled
workflow doesn't fail -- it just means Trend hasn't queued a new script yet.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_video import build
from upload_youtube import upload

EPISODES_DIR = os.path.join(os.path.dirname(__file__), "..", "content", "episodes")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "_build")


def find_next_episode():
    for path in sorted(glob.glob(os.path.join(EPISODES_DIR, "*.json"))):
        with open(path) as f:
            ep = json.load(f)
        if ep.get("status", "ready") == "ready":
            return path, ep
    return None, None


def main():
    path, ep = find_next_episode()
    if not ep:
        print("No ready episode queued. Nothing to do.")
        return

    print(f"Building episode: {ep['id']}")
    os.makedirs(OUT_DIR, exist_ok=True)
    video_path = build(path, OUT_DIR)
    print("Video built:", video_path)

    video_id = upload(video_path, path)

    ep["status"] = "published"
    ep["youtube_video_id"] = video_id
    with open(path, "w") as f:
        json.dump(ep, f, indent=2)
        f.write("\n")

    print(f"Episode {ep['id']} marked published as {video_id} (private -- review in Studio).")


if __name__ == "__main__":
    main()
