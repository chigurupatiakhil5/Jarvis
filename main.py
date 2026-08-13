import os
from dotenv import load_dotenv

load_dotenv()

from memory.logger import init_db
from agents.orchestrator import handle_command

INPUT_MODE = os.environ.get("INPUT_MODE", "voice")
OUTPUT_MODE = os.environ.get("OUTPUT_MODE", "voice")


def get_command() -> str:
    if INPUT_MODE == "wake":
        from voice.wake_word import wait_for_wake_word
        from voice.speech_to_text import listen_after_wake_word
        wait_for_wake_word()
        print("Yes, boss?")
        if OUTPUT_MODE == "voice":
            from voice.text_to_speech import speak
            speak("Yes, boss?")
        text = listen_after_wake_word()
        print(f"you (heard)> {text}")
        return text.strip()
    if INPUT_MODE == "voice":
        from voice.speech_to_text import listen
        text = listen()
        print(f"you (heard)> {text}")
        return text.strip()
    return input("you> ").strip()


def respond(text: str) -> None:
    print(f"\njarvis> {text}\n")
    if OUTPUT_MODE == "voice":
        from voice.text_to_speech import speak
        speak(text)


def main():
    init_db()
    mode_labels = {"wake": "Say 'Hey Jarvis' to activate", "voice": "Speak a command"}
    mode_label = mode_labels.get(INPUT_MODE, "Type a command")
    print(f"Jarvis is ready. {mode_label}, or say/type 'exit' to quit.\n")

    while True:
        command = get_command()
        if not command:
            continue
        if command.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        try:
            result = handle_command(command)
            respond(result)
        except Exception as e:
            respond(f"Something went wrong: {e}")


if __name__ == "__main__":
    main()
