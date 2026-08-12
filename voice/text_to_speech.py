import subprocess

_VOICE = "Samantha"


def speak(text: str) -> None:
    subprocess.run(["say", "-v", _VOICE, text])
