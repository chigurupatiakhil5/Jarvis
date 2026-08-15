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
_PIPER_SERVER_URL = os.environ.get("PIPER_SERVER_URL", "http://localhost:5001")
_CACHE_DIR = "voice/cache"

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


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
def _call_piper(text: str) -> bytes:
    response = httpx.post(
        f"{_PIPER_SERVER_URL}/synthesize",
        json={"text": text},
        timeout=30.0,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Piper server error {response.status_code}: {response.text}")
    return response.content


def _synthesize(text: str):
    """Returns (audio_bytes, file_extension) for the configured cloud-capable
    provider, or (None, None) if TTS_PROVIDER is "say" (local-only, no bytes)."""
    text = _normalize_for_speech(text)
    if _TTS_PROVIDER == "elevenlabs":
        return _call_elevenlabs(text), "mp3"
    if _TTS_PROVIDER == "piper":
        return _call_piper(text), "wav"
    return None, None


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
    if _TTS_PROVIDER in ("elevenlabs", "piper"):
        try:
            audio_bytes, extension = _synthesize(text)
            with tempfile.NamedTemporaryFile(suffix=f".{extension}", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name
            process = subprocess.Popen(["afplay", temp_path])
            _cleanup_when_done(process, temp_path)
            return process
        except RetryError as e:
            underlying = e.last_attempt.exception()
            print(f"[{_TTS_PROVIDER} unavailable, falling back to local voice: {underlying}]")
        except Exception as e:
            print(f"[{_TTS_PROVIDER} unavailable, falling back to local voice: {e}]")

    return subprocess.Popen(["say", "-v", _SAY_VOICE, _normalize_for_speech(text)])


def speak(text: str) -> None:
    """Speaks text and blocks until it finishes. For callers that don't need interruption."""
    speak_process(text).wait()


def speak_process_cached(text: str, cache_key: str) -> subprocess.Popen:
    """
    Like speak_process, but for a fixed, frequently-repeated phrase (like the
    "Yes, boss?" wake acknowledgment) — generates the audio once, caches it to
    disk, and plays the cached file instantly on every later call instead of
    hitting the API/server fresh each time.
    """
    if _TTS_PROVIDER not in ("elevenlabs", "piper"):
        return speak_process(text)

    os.makedirs(_CACHE_DIR, exist_ok=True)
    extension = "mp3" if _TTS_PROVIDER == "elevenlabs" else "wav"
    cache_path = os.path.join(_CACHE_DIR, f"{cache_key}.{extension}")

    if not os.path.exists(cache_path):
        try:
            audio_bytes, _ = _synthesize(text)
            with open(cache_path, "wb") as f:
                f.write(audio_bytes)
        except Exception as e:
            print(f"[{_TTS_PROVIDER} unavailable, falling back to local voice: {e}]")
            return subprocess.Popen(["say", "-v", _SAY_VOICE, _normalize_for_speech(text)])

    return subprocess.Popen(["afplay", cache_path])


def synthesize_bytes(text: str):
    """
    Returns (audio_bytes, mime_type) for the configured cloud-capable provider,
    or (None, None) if unavailable — for callers (like the cloud API) that need
    to send audio elsewhere rather than play it locally with `say`/`afplay`,
    which don't exist on a server.
    """
    if _TTS_PROVIDER not in ("elevenlabs", "piper"):
        return None, None
    try:
        audio_bytes, extension = _synthesize(text)
        mime_type = "audio/mpeg" if extension == "mp3" else "audio/wav"
        return audio_bytes, mime_type
    except Exception as e:
        print(f"[synthesize_bytes: {_TTS_PROVIDER} failed: {e}]")
        return None, None
