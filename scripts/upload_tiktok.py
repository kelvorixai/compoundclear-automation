"""
Uploads a finished MP4 to the CompoundClear TikTok account via TikTok's
Content Posting API (Direct Post), mirroring upload_youtube.py's pattern.

Auth: a long-lived OAuth refresh token (obtained once via a browser
consent flow -- see ../SETUP_GUIDE.md) exchanged at runtime for a fresh
access token. Nothing is ever stored except the refresh token itself, as
a GitHub Actions secret.

Env vars required:
  TIKTOK_CLIENT_KEY
  TIKTOK_CLIENT_SECRET
  TIKTOK_REFRESH_TOKEN

Usage:
  python upload_tiktok.py <video.mp4> <episode.json>
Prints the resulting publish_id on success.

Notes on TikTok's posting model (different enough from YouTube's to spell
out): there is no separate "set title/description then upload video" step
-- everything is one call. Posting is asynchronous: publish/video/init/
returns a publish_id and an upload_url, the video bytes are PUT to that
upload_url directly (not through this API's own auth), and the caller
then polls publish/status/fetch/ until TikTok reports the post finished
processing. A freshly-created app (this one, still unaudited by TikTok)
has all posts forced to SELF_ONLY (private) visibility regardless of what
privacy_level is requested here -- that restriction lifts once the app
passes TikTok's audit for public posting, not before. Until then this is
still useful for the sandbox target-user test account, but do not expect
public posts to actually go live.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB; TikTok requires the last chunk to
# be <= 64MB and total video <= 4GB for this flow -- fine for our short
# vertical episodes, which are a few tens of MB at most.


def _post_json(url, payload, access_token=None, extra_headers=None):
    headers = {"Content-Type": "application/json; charset=UTF-8"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {url} failed ({e.code}): {body}") from None


def get_access_token():
    """Exchanges the long-lived refresh token for a short-lived access
    token. Refresh tokens themselves also rotate on each use -- TikTok
    returns a new one in the response, but we don't attempt to persist it
    back to the GitHub Actions secret automatically (that would need
    write access to the repo's secrets from inside a workflow run, which
    is more risk than it's worth for a token that's typically valid for
    ~365 days). If TikTok ever shortens that lifetime, this will need a
    proper rotation step; flag it if refreshes start failing.
    """
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = urllib.parse.urlencode(
        {
            "client_key": os.environ["TIKTOK_CLIENT_KEY"],
            "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": os.environ["TIKTOK_REFRESH_TOKEN"],
        }
    ).encode("utf-8")
    req = urllib.request.Request(TOKEN_URL, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"TikTok token refresh failed ({e.code}): "
            f"{e.read().decode('utf-8', errors='replace')}"
        ) from None
    if "access_token" not in body:
        raise RuntimeError(f"TikTok token refresh returned no access_token: {body}")
    return body["access_token"]


def upload(video_path, episode_path):
    with open(episode_path) as f:
        ep = json.load(f)

    access_token = get_access_token()

    video_size = os.path.getsize(video_path)
    chunk_size = min(CHUNK_SIZE, video_size)
    total_chunks = max(1, (video_size + chunk_size - 1) // chunk_size)

    caption = ep.get("tiktok_caption", ep.get("title", ""))

    init_payload = {
        "post_info": {
            "title": caption,
            "privacy_level": ep.get("tiktok_privacy_level", "SELF_ONLY"),
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            # TikTok requires creators to disclose AI-generated/synthetic
            # content -- keep this true by default, matching the
            # disclosure-on stance already used for the YouTube uploads.
            "brand_content_toggle": False,
            "brand_organic_toggle": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunks,
        },
    }

    init_resp = _post_json(INIT_URL, init_payload, access_token=access_token)
    if "data" not in init_resp or "publish_id" not in init_resp["data"]:
        raise RuntimeError(f"TikTok publish init failed: {init_resp}")

    publish_id = init_resp["data"]["publish_id"]
    upload_url = init_resp["data"]["upload_url"]

    # Upload the video bytes directly to the returned upload_url, chunked
    # per the sizes we told TikTok to expect in source_info above.
    with open(video_path, "rb") as f:
        for chunk_index in range(total_chunks):
            start = chunk_index * chunk_size
            f.seek(start)
            data = f.read(chunk_size)
            end = start + len(data) - 1
            headers = {
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes {start}-{end}/{video_size}",
                "Content-Length": str(len(data)),
            }
            req = urllib.request.Request(upload_url, data=data, headers=headers, method="PUT")
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    resp.read()
            except urllib.error.HTTPError as e:
                raise RuntimeError(
                    f"TikTok chunk upload failed at chunk {chunk_index} "
                    f"({e.code}): {e.read().decode('utf-8', errors='replace')}"
                ) from None
            print(f"upload progress: chunk {chunk_index + 1}/{total_chunks}")

    # Poll for TikTok to finish processing the upload. This can take from
    # a few seconds to a couple of minutes depending on video length.
    status = None
    for _ in range(60):  # up to ~5 minutes at 5s intervals
        status_resp = _post_json(
            STATUS_URL, {"publish_id": publish_id}, access_token=access_token
        )
        status = status_resp.get("data", {}).get("status")
        print(f"publish status: {status}")
        if status in ("PUBLISH_COMPLETE", "FAILED"):
            break
        time.sleep(5)

    if status == "FAILED":
        fail_reason = status_resp.get("data", {}).get("fail_reason", "unknown")
        raise RuntimeError(f"TikTok publish failed: {fail_reason}")

    print("PUBLISHED:", publish_id)
    return publish_id


if __name__ == "__main__":
    video_path, episode_path = sys.argv[1], sys.argv[2]
    upload(video_path, episode_path)
