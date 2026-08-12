import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

_SAMPLE_RATE = 16000
_MODEL_SIZE = "tiny"

_model = WhisperModel(_MODEL_SIZE, device="cpu", compute_type="int8")


def _record_until_enter() -> np.ndarray:
    frames = []

    def _callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    with sd.InputStream(samplerate=_SAMPLE_RATE, channels=1, dtype="float32", callback=_callback):
        input()

    return np.concatenate(frames, axis=0).flatten()


def listen() -> str:
    input("Press Enter to start speaking...")
    print("Listening... press Enter when you're done.")
    audio = _record_until_enter()

    print("Transcribing... (first run per session can take a bit longer)")
    segments, _ = _model.transcribe(audio, language="en")
    text = " ".join(segment.text.strip() for segment in segments)
    return text.strip()
