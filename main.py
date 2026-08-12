import os
from dotenv import load_dotenv

load_dotenv()

from memory.logger import init_db
from agents.orchestrator import handle_command

INPUT_MODE = os.environ.get("INPUT_MODE", "voice")
OUTPUT_MODE = os.environ.get("OUTPUT_MODE", "voice")


def get_command() -> str:
    if INPUT_MODE == "voice":
        from voice.speech_to_text import listen
        text = listen()
        print(f"you (heard)> {text}")
        return text.strip()
    return input("you> ").strip()


def respond(text: str) -> None:
    print(f"\nmay> {text}\n")
    if OUTPUT_MODE == "voice":
        from voice.text_to_speech import speak
        speak(text)


def main():
    init_db()
    mode_label = "Speak a command" if INPUT_MODE == "voice" else "Type a command"
    print(f"May is ready. {mode_label}, or say/type 'exit' to quit.\n")

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
