# CompoundClear automation

Fully automated pipeline for the CompoundClear YouTube channel (Kelvorix AI
- YouTube division). Runs on GitHub Actions on a schedule, independent of
any local machine:

Queued episode (content/episodes/*.json) -> Piper (free, offline) TTS narration ->
branded slide rendering -> ffmpeg video assembly -> upload to YouTube as
private for review.

See SETUP_GUIDE.md for the one-time setup only a human can do (YouTube
OAuth consent). Everything else runs unattended, at zero cost, with no
credit card required anywhere in the pipeline.

## Layout

- content/episodes/ -- one JSON file per video (script + slide data + metadata)
- scripts/tts_piper.py -- local offline neural TTS via Piper (free, no account)
- scripts/slides.py -- branded slide rendering (PIL + matplotlib)
- scripts/build_video.py -- assembles narration + slides into an MP4 (ffmpeg)
- scripts/upload_youtube.py -- uploads to YouTube via the Data API v3
- scripts/run_pipeline.py -- orchestrates the above, run by the workflow
- scripts/get_refresh_token.py -- one-time local script to obtain a YouTube OAuth refresh token
- .github/workflows/publish.yml -- the scheduled job

## Safety

- Uploads always land as private. Nothing is ever made public without a
  human clicking publish in YouTube Studio.
- All narration, visuals, and scripts are original / synthesized --
  no scraped footage, no cloned voices, no copyrighted material.
- AI-generated disclosure should be set on each upload per YouTube's
  synthetic-media policy (see SETUP_GUIDE.md notes).
