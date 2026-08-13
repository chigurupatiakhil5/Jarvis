import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from groq import Groq
from memory.logger import init_db, get_preferences, get_recent_notifications, log_event
from tools.weather import get_weather
from voice.text_to_speech import speak

_client = Groq(api_key=os.environ["GROQ_API_KEY"])
_CHECK_INTERVAL_SECONDS = int(os.environ.get("SCHEDULER_CHECK_INTERVAL_MINUTES", "30")) * 60

_SYSTEM_PROMPT = (
    "You are Jarvis's background monitor. You are given the current weather conditions, "
    "a list of things the user has said they care about, and what you've already told the "
    "user recently. Decide if any preference is matched by the current conditions right now, "
    "strongly enough to be worth proactively telling the user about. Do not repeat something "
    "you've already told them recently unless conditions changed meaningfully since then. "
    'Respond with ONLY valid JSON: {"should_notify": true or false, "message": "<what to say, if true>"}'
)


def _check_once() -> None:
    preferences = get_preferences()
    if not preferences:
        return

    weather = get_weather()
    recent = get_recent_notifications(hours=6)

    preferences_block = "\n".join(f"- {p}" for p in preferences)
    recent_block = "\n".join(f"- {m}" for m in recent) if recent else "(nothing recently)"
    weather_block = (
        f"Temperature: {weather['temperature_f']}°F\n"
        f"Wind speed: {weather['wind_speed_mph']} mph\n"
        f"Precipitation: {weather['precipitation_in']} in\n"
        f"Cloud cover: {weather['cloud_cover_pct']}%\n"
        f"Sunset today: {weather['sunset_today']}\n"
        f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    response = _client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Preferences:\n{preferences_block}\n\n"
                    f"Current conditions:\n{weather_block}\n\n"
                    f"Already told the user recently:\n{recent_block}"
                ),
            },
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)

    if result.get("should_notify"):
        message = result["message"]
        print(f"\njarvis (proactive)> {message}\n")
        speak(message)
        log_event("scheduler", "notify", weather_block, message, status="success")
    else:
        log_event("scheduler", "check", weather_block, "no notification", status="success")


def main():
    init_db()
    print(f"Jarvis background monitor started. Checking every {_CHECK_INTERVAL_SECONDS // 60} minutes.")
    while True:
        try:
            _check_once()
        except Exception as e:
            print(f"[scheduler check failed: {e}]")
        time.sleep(_CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
