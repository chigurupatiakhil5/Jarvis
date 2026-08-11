"""
Local speech-to-text using faster-whisper — a fast reimplementation of
OpenAI's Whisper model. Runs entirely on your machine: no API key, no cost,
no audio ever leaves your computer.

Interaction model: press Enter to start, speak, press Enter again to stop
(push-to-talk). Continuous always-listening comes later, with wake-word
detection in v5.
"""

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

_SAMPLE_RATE = 16000
_MODEL_SIZE = "base"

# Loaded once at import time (not per-command) — loading model weights is the
# slow part; transcribing a few seconds of audio with it is fast.
_model = WhisperModel(_MODEL_SIZE, device="cpu", compute_type="int8")


def _record_until_enter() -> np.ndarray:
    """Record audio from the default microphone until the user presses Enter."""
    frames = []

    def _callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    with sd.InputStream(samplerate=_SAMPLE_RATE, channels=1, dtype="float32", callback=_callback):
        input()  # blocks here; recording continues in the background via _callback

    return np.concatenate(frames, axis=0).flatten()


def listen() -> str:
    """
    Record from the microphone and transcribe it to text.
    Prompts you to start, then to stop, then returns the transcribed text.
    """
    input("Press Enter to start speaking...")
    print("Listening... press Enter when you're done.")
    audio = _record_until_enter()

    segments, _ = _model.transcribe(audio, language="en")
    text = " ".join(segment.text.strip() for segment in segments)
    return text.strip()
