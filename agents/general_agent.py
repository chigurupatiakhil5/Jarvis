import os
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from memory.logger import log_event, get_preferences

_client = Groq(api_key=os.environ["GROQ_API_KEY"])


def _build_system_prompt(user_id: str) -> str:
    preferences = get_preferences(user_id)
    preferences_block = "\n".join(f"- {p}" for p in preferences) if preferences else "(none saved yet)"
    return (
        "You are the General Agent inside Jarvis, a multi-agent assistant. "
        "You are given a general question or casual message that doesn't need real-time web "
        "data, file creation, code execution, or email drafting. "
        "Answer directly and conversationally from your own knowledge, in a few sentences. "
        f"The user's saved preferences (use these ONLY if they ask what they like, what they've "
        f"told you before, or something similar — ignore them otherwise):\n{preferences_block}\n"
        "If the question is about their preferences and the list above is non-empty, you MUST "
        "summarize from that list — never claim you have no information when the list has entries."
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
def _call_llm(user_id: str, instruction: str) -> str:
    response = _client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _build_system_prompt(user_id)},
            {"role": "user", "content": instruction},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def run(user_id: str, instruction: str) -> str:
    try:
        answer = _call_llm(user_id, instruction)
        log_event(user_id, "general_agent", "answer", instruction, answer, status="success")
        return answer
    except Exception as e:
        log_event(user_id, "general_agent", "answer", instruction, str(e), status="error")
        raise
