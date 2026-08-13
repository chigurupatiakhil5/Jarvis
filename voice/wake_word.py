import os
import threading
import sounddevice as sd
from openwakeword.model import Model

_SAMPLE_RATE = 16000
_CHUNK_SIZE = 1280
_THRESHOLD = 0.3
_MODEL_NAME = os.environ.get("WAKE_WORD_MODEL", "hey_jarvis")

_model = Model(wakeword_models=[_MODEL_NAME], inference_framework="onnx")
_WARMUP_CHUNKS = 16


def wait_for_wake_word(stop_event: threading.Event = None, announce: bool = True) -> bool:
    """
    Blocks until the wake word is detected, returning True.
    If stop_event is provided and gets set from another thread, returns False
    instead (used to cancel a background listener once it's no longer needed).
    """
    with sd.InputStream(samplerate=_SAMPLE_RATE, channels=1, dtype="int16", blocksize=_CHUNK_SIZE) as stream:
        for _ in range(_WARMUP_CHUNKS):
            frame, _ = stream.read(_CHUNK_SIZE)
            _model.predict(frame.flatten())

        if announce:
            print("Listening for 'Hey Jarvis'...")

        while True:
            if stop_event is not None and stop_event.is_set():
                return False

            frame, _ = stream.read(_CHUNK_SIZE)
            predictions = _model.predict(frame.flatten())
            score = list(predictions.values())[0]
            if score > _THRESHOLD:
                _model.reset()
                return True
