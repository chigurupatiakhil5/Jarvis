import os
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from memory.logger import save_preference, log_event

_client = Groq(api_key=os.environ["GROQ_API_KEY"])

_SYSTEM_PROMPT = (
    "You are the Preferences Agent inside Jarvis, a multi-agent assistant. "
    "You are given an instruction where the user is telling you something they like, "
    "want to be notified about, or care about. "
    "Rewrite it as a single short, clear preference statement (one sentence, no preamble) "
    "that could later be checked against real-world conditions. "
    "Example: 'remember I like it when it's rainy and windy with no sun so I can go out and chill' "
    "-> 'Likes rainy, windy weather with no direct sun — good time to suggest going outside.'"
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
def _call_llm(instruction: str) -> str:
    response = _client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def run(user_id: str, instruction: str) -> str:
    try:
        preference = _call_llm(instruction)
        log_event(user_id, "preferences_agent", "distill", instruction, preference, status="success")
    except Exception as e:
        log_event(user_id, "preferences_agent", "distill", instruction, str(e), status="error")
        raise

    try:
        save_preference(user_id, preference)
        log_event(user_id, "preferences_agent", "save", preference, "saved", status="success")
    except Exception as e:
        log_event(user_id, "preferences_agent", "save", preference, str(e), status="error")
        raise

    return f"Got it — I'll remember: {preference}"
