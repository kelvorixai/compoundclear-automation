"""
ONE-TIME LOCAL SCRIPT -- run this on your own computer, not in CI.

It opens a browser, asks you to sign in with the Google account that
manages the CompoundClear channel, and prints a refresh token you paste
into the YOUTUBE_REFRESH_TOKEN GitHub secret. Nothing here touches your
actual password -- this is the standard Google OAuth consent screen.

Setup (see SETUP_GUIDE.md for the full walkthrough):
  pip install google-auth-oauthlib
  python get_refresh_token.py --client-id XXX --client-secret YYY
"""
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

parser = argparse.ArgumentParser()
parser.add_argument("--client-id", required=True)
parser.add_argument("--client-secret", required=True)
args = parser.parse_args()

client_config = {
    "installed": {
        "client_id": args.client_id,
        "client_secret": args.client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
# Opens your default browser; after you approve, it captures the code via
# a temporary local server on an available port.
creds = flow.run_local_server(port=0)

print("\n\nSUCCESS. Add this as the YOUTUBE_REFRESH_TOKEN secret:\n")
print(creds.refresh_token)
