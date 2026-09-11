"""
Top-level orchestrator run by the GitHub Actions workflow.

Processes every episode JSON in content/episodes/ currently marked "ready"
(falls back to no status field = ready, for hand-authored episodes) in one
run -- not just the first one -- so a day's whole batch of newly-queued
episodes gets built and uploaded in a single workflow invocation instead of
needing one workflow_dispatch per episode.

For each ready episode:
1. Builds the video (TTS + slides + ffmpeg assembly).
2. Uploads it to YouTube (visibility per the episode's own privacy_status,
   private by default -- see upload_youtube.py).
3. Marks the episode "published" with the resulting video_id.

If a given episode fails to build or upload, its error is printed and the
episode is left as "ready" (not marked published) so it's retried on the
next run; the pipeline moves on to the remaining ready episodes rather than
aborting the whole batch over one bad file.

If no ready episodes exist, exits cleanly (status 0) so the scheduled
workflow doesn't fail -- it just means nothing new has been queued yet.
"""
import glob
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(__file__))
from build_video import build
from upload_youtube import upload

EPISODES_DIR = os.path.join(os.path.dirname(__file__), "..", "content", "episodes")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "_build")


def find_ready_episodes():
    ready = []
    for path in sorted(glob.glob(os.path.join(EPISODES_DIR, "*.json"))):
        with open(path) as f:
            ep = json.load(f)
        if ep.get("status", "ready") == "ready":
            ready.append((path, ep))
    return ready


def process_one(path, ep):
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

    print(f"Episode {ep['id']} marked published as {video_id}.")


def main():
    ready = find_ready_episodes()
    if not ready:
        print("No ready episodes queued. Nothing to do.")
        return

    print(f"Found {len(ready)} ready episode(s).")
    failures = []
    for path, ep in ready:
        try:
            process_one(path, ep)
        except Exception:
            print(f"FAILED to process {ep.get('id', path)}:")
            traceback.print_exc()
            failures.append(ep.get("id", path))
            # Leave this episode as "ready" so it's retried on the next
            # run; keep going with the rest of today's batch.
            continue

    if failures:
        # Don't exit non-zero here: some episodes may have published
        # successfully and we still want the workflow's next step to
        # commit those status changes rather than skip on job failure.
        print(f"Completed with {len(failures)} failure(s): {', '.join(failures)}")
    else:
        print("All ready episodes processed successfully.")


if __name__ == "__main__":
    main()
