"""
Entry point for May.
Run this to start the assistant: `python main.py` (or via docker compose).
"""

from dotenv import load_dotenv

load_dotenv()

from memory.logger import init_db
from agents.orchestrator import handle_command


def main():
    init_db()
    print("May is ready. Type a command, or 'exit' to quit.\n")

    while True:
        command = input("you> ").strip()
        if not command:
            continue
        if command.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        try:
            result = handle_command(command)
            print(f"\nmay> {result}\n")
        except Exception as e:
            print(f"\nmay> Something went wrong: {e}\n")


if __name__ == "__main__":
    main()
