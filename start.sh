#!/bin/bash
set -e

# Render assigns the port to listen on via $PORT — must bind 0.0.0.0, not
# localhost, so traffic from outside the container can reach it.
#
# Piper isn't started here — the deployed backend uses ElevenLabs for TTS
# instead (TTS_PROVIDER=elevenlabs in Render's env vars), since running
# Piper's own model alongside Whisper exceeded the free tier's 512MB RAM
# limit. The local Mac app still uses Piper directly (unlimited, no memory
# constraint on your own hardware).
exec uvicorn api:app --host 0.0.0.0 --port "${PORT:-8001}"
