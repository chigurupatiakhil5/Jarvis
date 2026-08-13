import os
import sounddevice as sd
from openwakeword.model import Model

_SAMPLE_RATE = 16000
_CHUNK_SIZE = 1280
_THRESHOLD = 0.5
_MODEL_NAME = os.environ.get("WAKE_WORD_MODEL", "hey_jarvis")

_model = Model(wakeword_models=[_MODEL_NAME], inference_framework="onnx")


def wait_for_wake_word() -> None:
    print("Listening for 'Hey Jarvis'...")
    with sd.InputStream(samplerate=_SAMPLE_RATE, channels=1, dtype="int16", blocksize=_CHUNK_SIZE) as stream:
        while True:
            frame, _ = stream.read(_CHUNK_SIZE)
            predictions = _model.predict(frame.flatten())
            score = list(predictions.values())[0]
            if score > _THRESHOLD:
                _model.reset()
                return
