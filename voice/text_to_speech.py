import os
import re
import subprocess
import tempfile
import threading
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

_SAY_VOICE = "Samantha"
_TTS_PROVIDER = os.environ.get("TTS_PROVIDER", "say")
_ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "")

_SPEECH_REPLACEMENTS = [
    (re.compile(r"°F", re.IGNORECASE), " degrees Fahrenheit"),
    (re.compile(r"°C", re.IGNORECASE), " degrees Celsius"),
    (re.compile(r"°"), " degrees"),
    (re.compile(r"\bmph\b", re.IGNORECASE), "miles per hour"),
    (re.compile(r"\bkm/h\b", re.IGNORECASE), "kilometers per hour"),
]


def _normalize_for_speech(text: str) -> str:
    for pattern, replacement in _SPEECH_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text


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


def _cleanup_when_done(process: subprocess.Popen, path: str) -> None:
    def _wait_and_remove():
        process.wait()
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    threading.Thread(target=_wait_and_remove, daemon=True).start()


def speak_process(text: str) -> subprocess.Popen:
    """
    Starts speaking `text` without blocking, returning the playback process
    so the caller can poll it or call .terminate() to stop mid-sentence.
    """
    text = _normalize_for_speech(text)

    if _TTS_PROVIDER == "elevenlabs":
        try:
            audio_bytes = _call_elevenlabs(text)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name
            process = subprocess.Popen(["afplay", temp_path])
            _cleanup_when_done(process, temp_path)
            return process
        except RetryError as e:
            underlying = e.last_attempt.exception()
            print(f"[ElevenLabs unavailable, falling back to local voice: {underlying}]")
        except Exception as e:
            print(f"[ElevenLabs unavailable, falling back to local voice: {e}]")

    return subprocess.Popen(["say", "-v", _SAY_VOICE, text])


def speak(text: str) -> None:
    """Speaks text and blocks until it finishes. For callers that don't need interruption."""
    speak_process(text).wait()
