"""
Google Cloud Text-to-Speech wrapper.

Auth: uses an API key (simplest -- no service-account JSON to manage as a
secret). The key must be restricted to the "Cloud Text-to-Speech API" in
Google Cloud Console > APIs & Services > Credentials.

Env var required: GOOGLE_TTS_API_KEY
"""
import base64
import os
import wave
import requests

ENDPOINT = "https://texttospeech.googleapis.com/v1/text:synthesize"

# A natural-sounding Neural2 voice. Swap to a "Studio" voice
# (e.g. en-US-Studio-O) for even higher quality if your project has access.
VOICE_NAME = "en-US-Neural2-D"
LANGUAGE_CODE = "en-US"
SAMPLE_RATE = 24000


def synth(text: str, out_path: str, speaking_rate: float = 1.0) -> float:
    """Synthesize `text` to a 16-bit PCM WAV at `out_path`.
    Returns the duration in seconds."""
    api_key = os.environ["GOOGLE_TTS_API_KEY"]
    payload = {
        "input": {"text": text},
        "voice": {"languageCode": LANGUAGE_CODE, "name": VOICE_NAME},
        "audioConfig": {
            "audioEncoding": "LINEAR16",
            "sampleRateHertz": SAMPLE_RATE,
            "speakingRate": speaking_rate,
        },
    }
    resp = requests.post(
        f"{ENDPOINT}?key={api_key}",
        json=payload,
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Google TTS error {resp.status_code}: {resp.text[:500]}")
    audio_b64 = resp.json()["audioContent"]
    audio_bytes = base64.b64decode(audio_b64)
    with open(out_path, "wb") as f:
        f.write(audio_bytes)
    with wave.open(out_path, "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate()
        return frames / float(rate)


if __name__ == "__main__":
    # quick smoke test: python tts_google.py "hello world" out.wav
    import sys
    d = synth(sys.argv[1], sys.argv[2])
    print("duration:", d)
