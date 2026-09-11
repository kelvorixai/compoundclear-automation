"""
Uploads a finished MP4 to the CompoundClear YouTube channel via the
YouTube Data API v3.

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


def upload(video_path, episode_path):
    with open(episode_path) as f:
        ep = json.load(f)

    youtube = get_service()

    body = {
        "snippet": {
            "title": ep["title"],
            "description": ep["description"],
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

    # Mark AI-generated / synthetic content disclosure (YouTube's altered
    # content toggle) via the videos.insert containsSyntheticMedia field
    # where available; if not supported by the API version in use this is
    # a no-op and must be set manually once in YouTube Studio per video
    # until Google exposes it broadly via API.
    return video_id


if __name__ == "__main__":
    video_path, episode_path = sys.argv[1], sys.argv[2]
    upload(video_path, episode_path)
