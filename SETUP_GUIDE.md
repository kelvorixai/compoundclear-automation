# CompoundClear automation -- one-time setup

This pipeline runs on GitHub Actions (free, always-on, works even when your
PC is off). It picks the next queued episode, synthesizes narration locally
with Piper (a free, offline, open-source neural TTS engine -- no account,
no API key, no billing, ever), renders the slides, assembles the video with
ffmpeg, and uploads it to YouTube as **private**. Nothing goes public
automatically -- you review each upload in YouTube Studio and flip it to
public yourself, or tell me to.

There's one thing only you can do (Google requires the account owner, not
an AI, to grant OAuth access). Roughly 10-15 minutes, one time only.

## 1. YouTube Data API v3 + OAuth client

1. In the Google Cloud project (compoundclear), APIs & Services -> Library
   -> enable YouTube Data API v3. (This one is free -- no billing account
   needed, unlike some other Cloud APIs.)
2. APIs & Services -> OAuth consent screen -> External -> fill the minimum
   (app name "CompoundClear Pipeline", your email) -> save. It's fine to
   leave it in "Testing" mode -- add your own Google account under
   "Test users".
3. APIs & Services -> Credentials -> Create Credentials -> OAuth client ID ->
   Application type Desktop app -> name it anything -> Create.
4. Copy the Client ID and Client Secret -- these become
   YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET.

## 2. Get a refresh token (run locally, once)

This has to happen in a real browser you control, signed into the Google
account that manages the CompoundClear channel/brand account.

pip install google-auth-oauthlib
python scripts/get_refresh_token.py --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET

It opens your browser, you approve access, and it prints a refresh token
in the terminal. Copy it -- this becomes YOUTUBE_REFRESH_TOKEN. This
token doesn't expire from use; it only stops working if you revoke access
in your Google Account security settings.

## 3. Add the three repo secrets

In this repo: Settings -> Secrets and variables -> Actions -> New repository
secret. Add:

- YOUTUBE_CLIENT_ID
- YOUTUBE_CLIENT_SECRET
- YOUTUBE_REFRESH_TOKEN

That's it. Once these three secrets exist, the workflow in
.github/workflows/publish.yml runs automatically on its schedule (Tue/Fri
14:00 UTC by default -- easy to change) and every run:

1. Picks the next "status": "ready" episode from content/episodes/
2. Synthesizes narration locally with Piper (free, offline)
3. Renders the branded slides and assembles the MP4
4. Uploads it to the CompoundClear channel as private
5. Marks that episode "published" in the repo so it isn't repeated

You'll get a private video sitting in YouTube Studio to review. Publishing
it further (public) is a manual click on your end unless you want that
automated too later.

## Adding new episodes

Each episode is one JSON file in content/episodes/. ep01_compound-interest.json
is a full working example. New topics (the remaining 7 from the original
batch, plus anything new) need their script + slide data written in this
same format before they'll be picked up -- that's the next thing to
produce once this pipeline is live and proven on episode 1.
