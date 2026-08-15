#!/bin/bash
set -e

# The voice model (.onnx) is gitignored, so a fresh checkout never has it —
# download it into the working directory before starting the server, which
# looks for it there by default.
python3 -m piper.download_voices en_GB-northern_english_male-medium

# Start Piper's TTS server in the background, in the same container as the
# API — PIPER_SERVER_URL=http://localhost:5001 only works if they're on the
# same machine, and this is the free way to get that on Render.
python3 -m piper.http_server -m en_GB-northern_english_male-medium --port 5001 &

# Give Piper a few seconds to start listening before the API starts
# serving real requests.
sleep 5

# Render assigns the port to listen on via $PORT — must bind 0.0.0.0, not
# localhost, so traffic from outside the container can reach it.
exec uvicorn api:app --host 0.0.0.0 --port "${PORT:-8001}"
