import os
import threading
import time
from dotenv import load_dotenv

load_dotenv()

from memory.logger import init_db
from agents.orchestrator import handle_command

INPUT_MODE = os.environ.get("INPUT_MODE", "voice")
OUTPUT_MODE = os.environ.get("OUTPUT_MODE", "voice")
_USER_ID = os.environ["MY_USER_ID"]


def _acknowledge_and_listen() -> str:
    from voice.speech_to_text import listen_after_wake_word
    print("Yes, boss?")
    if OUTPUT_MODE == "voice":
        from voice.text_to_speech import speak_process_cached
        speak_process_cached("Yes, boss?", "yes_boss").wait()
    text = listen_after_wake_word()
    print(f"you (heard)> {text}")
    return text.strip()


def get_command() -> str:
    if INPUT_MODE == "wake":
        from voice.wake_word import wait_for_wake_word
        wait_for_wake_word()
        return _acknowledge_and_listen()
    if INPUT_MODE == "voice":
        from voice.speech_to_text import listen
        text = listen()
        print(f"you (heard)> {text}")
        return text.strip()
    return input("you> ").strip()


def respond(text: str):
    """
    Prints and speaks `text`. In wake mode with voice output, listens for an
    interrupting "Hey Jarvis" while speaking — if heard, stops speaking early
    and returns the next command directly. Otherwise returns None.
    """
    print(f"\njarvis> {text}\n")

    if OUTPUT_MODE != "voice":
        return None

    if INPUT_MODE != "wake":
        from voice.text_to_speech import speak
        speak(text)
        return None

    from voice.wake_word import wait_for_wake_word
    from voice.text_to_speech import speak_process

    stop_listening = threading.Event()
    wake_detected = threading.Event()

    def _listen_in_background():
        if wait_for_wake_word(stop_event=stop_listening, announce=False, use_barge_in_model=True):
            wake_detected.set()

    listener_thread = threading.Thread(target=_listen_in_background, daemon=True)
    listener_thread.start()

    process = speak_process(text)
    while process.poll() is None:
        if wake_detected.is_set():
            process.terminate()
            process.wait(timeout=2)
            break
        time.sleep(0.05)

    stop_listening.set()
    listener_thread.join()

    if wake_detected.is_set():
        return _acknowledge_and_listen()
    return None


def main():
    init_db()
    mode_labels = {"wake": "Say 'Hey Jarvis' to activate", "voice": "Speak a command"}
    mode_label = mode_labels.get(INPUT_MODE, "Type a command")
    print(f"Jarvis is ready. {mode_label}, or say/type 'exit' to quit.\n")

    pending_command = None

    while True:
        command = pending_command or get_command()
        pending_command = None

        if not command:
            continue
        if command.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        try:
            result = handle_command(_USER_ID, command)
            pending_command = respond(result)
        except Exception as e:
            pending_command = respond(f"Something went wrong: {e}")


if __name__ == "__main__":
    main()
