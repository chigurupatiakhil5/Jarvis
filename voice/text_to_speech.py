import os
import subprocess
import tempfile
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

_SAY_VOICE = "Samantha"
_TTS_PROVIDER = os.environ.get("TTS_PROVIDER", "say")
_ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "")


def _speak_with_say(text: str) -> None:
    subprocess.run(["say", "-v", _SAY_VOICE, text])


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
def _call_elevenlabs(text: str) -> bytes:
    response = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{_ELEVENLABS_VOICE_ID}",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
        json={"text": text, "model_id": "eleven_multilingual_v2"},
        timeout=30.0,
    )
    if response.status_code != 200:
        raise RuntimeError(f"ElevenLabs API error {response.status_code}: {response.text}")
    return response.content


def _speak_with_elevenlabs(text: str) -> None:
    audio_bytes = _call_elevenlabs(text)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(audio_bytes)
        temp_path = f.name
    try:
        subprocess.run(["afplay", temp_path])
    finally:
        os.remove(temp_path)


def speak(text: str) -> None:
    if _TTS_PROVIDER == "elevenlabs":
        try:
            _speak_with_elevenlabs(text)
            return
        except RetryError as e:
            underlying = e.last_attempt.exception()
            print(f"[ElevenLabs unavailable, falling back to local voice: {underlying}]")
        except Exception as e:
            print(f"[ElevenLabs unavailable, falling back to local voice: {e}]")

    _speak_with_say(text)
