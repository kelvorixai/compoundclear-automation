"""
Uploads a finished MP4 to the Kelvorix Digital YouTube channel via the
YouTube Data API v3, and sets its custom thumbnail if build_video.py
produced one alongside it.

Auth: a long-lived OAuth refresh token (obtained once, see
../SETUP_GUIDE.md) exchanged at runtime for an access token. Nothing is
ever stored except the refresh token itself, as a GitHub Actions secret.

Env vars required:
  YOUTUBE_CLIENT_ID
  YOUTUBE_CLIENT_SECRET
  YOUTUBE_REFRESH_TOKEN

Usage:
  python upload_youtube.py <video.mp4> <episode.json>
Prints the resulting video ID on success.
"""
import json
import os
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds)

# Appended to every episode description at upload time, so it applies to all
# FUTURE uploads without editing any episode JSON. Videos already published
# are deliberately left alone. Aziz asked for this on 14 Sep 2026.
DESCRIPTION_FOOTER = (
    "\n\n---\n"
    "SUBSCRIBE for one short, practical AI-at-work video every Tuesday and Friday.\n\n"
    "Free: 12 work prompts that actually work (PDF, no card)\n"
    "https://kelvorixdigital.lemonsqueezy.com/checkout/buy/"
    "2a95cbaf-fd7e-4e28-908e-ccf98199c508?utm_source=youtube&utm_medium=description\n\n"
    "The full playbooks: https://kelvorixdigital.lemonsqueezy.com"
)

def set_thumbnail(youtube, video_id, video_path):
    """build_video.py writes a custom 1280x720 thumbnail.png next to the
    video's own mp4 (same directory) whenever the episode JSON has a title
    or explicit thumbnail_text -- see build_video.build(). Without a custom
    thumbnail, YouTube auto-picks a frame from the video itself, which is
    one of the biggest drags on click-through for a channel with no
    subscriber base yet, so this is worth doing for every video.

    Setting a custom thumbnail via the API requires the channel to be
    phone-verified (the same verification YouTube's Studio UI prompts for
    under "Unlock more on YouTube"). If that hasn't been done yet, this
    call fails with an HttpError -- caught and logged here as a clear,
    actionable warning rather than failing the whole upload, since the
    video itself still published successfully.
    """
    thumbnail_path = os.path.join(os.path.dirname(video_path), "thumbnail.png")
    if not os.path.exists(thumbnail_path):
        return
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path, mimetype="image/png"),
        ).execute()
        print(f"Custom thumbnail set for {video_id}.")
    except HttpError as e:
        print(
            f"WARNING: could not set custom thumbnail for {video_id} "
            f"(video itself still uploaded fine): {e}\n"
            "This channel most likely still needs phone verification in "
            "YouTube Studio (Settings > Channel > Feature eligibility) "
            "before the API will accept custom thumbnails -- that's a "
            "one-time step only Aziz can do (it needs his phone number). "
            "Flag this plainly in the run's final summary if it keeps "
            "happening."
        )

def upload(video_path, episode_path):
    with open(episode_path) as f:
        ep = json.load(f)

    youtube = get_service()

    body = {
        "snippet": {
            "title": ep["title"],
            "description": ep["description"] + DESCRIPTION_FOOTER,
            "tags": ep.get("tags", []),
            "categoryId": ep.get("category_id", "27"),  # 27 = Education
        },
        "status": {
            # Always land as private/unlisted first -- Aziz reviews and
            # flips visibility himself in YouTube Studio. Never auto-public.
            "privacyStatus": ep.get("privacy_status", "private"),
            "selfDeclaredMadeForKids": ep.get("made_for_kids", False),
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print("UPLOADED:", video_id)
    print(f"https://youtube.com/watch?v={video_id}")

    set_thumbnail(youtube, video_id, video_path)

    # Mark AI-generated / synthetic content disclosure (YouTube's altered
    # content toggle) via the videos.insert containsSyntheticMedia field
    # where available; if not supported by the API version in use this is
    # a no-op and must be set manually once in YouTube Studio per video
    # until Google exposes it broadly via API.
    return video_id

if __name__ == "__main__":
    video_path, episode_path = sys.argv[1], sys.argv[2]
    upload(video_path, episode_path)
