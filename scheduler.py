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
_USER_ID = os.environ["MY_USER_ID"]

_SYSTEM_PROMPT = (
    "You are Jarvis's background monitor. You are given the current weather conditions "
    "(including exactly how many minutes until/since sunset, already calculated for you — "
    "use that number directly, do not try to recompute it yourself from timestamps), a list "
    "of things the user has said they care about, and what you've already told the user "
    "recently. Decide if any preference is matched by the current conditions right now, "
    "strongly enough to be worth proactively telling the user about. For sunset-related "
    "preferences, only notify when sunset is within about 30 minutes (before or after) — "
    "never hours away. Do not repeat something you've already told them recently unless "
    "conditions changed meaningfully since then. "
    'Respond with ONLY valid JSON: {"should_notify": true or false, "message": "<what to say, if true>"}'
)


def _minutes_until(target_iso: str) -> int:
    target = datetime.fromisoformat(target_iso)
    return int((target - datetime.now()).total_seconds() / 60)


def _check_once() -> None:
    preferences = get_preferences(_USER_ID)
    if not preferences:
        return

    weather = get_weather()
    recent = get_recent_notifications(_USER_ID, hours=6)

    sunset_minutes = _minutes_until(weather["sunset_today"])
    sunset_description = f"in {sunset_minutes} minutes" if sunset_minutes >= 0 else f"{-sunset_minutes} minutes ago"

    preferences_block = "\n".join(f"- {p}" for p in preferences)
    recent_block = "\n".join(f"- {m}" for m in recent) if recent else "(nothing recently)"
    weather_block = (
        f"Temperature: {weather['temperature_f']}°F\n"
        f"Wind speed: {weather['wind_speed_mph']} mph\n"
        f"Precipitation: {weather['precipitation_in']} in\n"
        f"Cloud cover: {weather['cloud_cover_pct']}%\n"
        f"Sunset today: {weather['sunset_today']} ({sunset_description})\n"
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
        log_event(_USER_ID, "scheduler", "notify", weather_block, message, status="success")
    else:
        log_event(_USER_ID, "scheduler", "check", weather_block, "no notification", status="success")


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
