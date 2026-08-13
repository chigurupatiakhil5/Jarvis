import os
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from memory.logger import log_event

_client = Groq(api_key=os.environ["GROQ_API_KEY"])

_SYSTEM_PROMPT = (
    "You are the General Agent inside Jarvis, a multi-agent assistant. "
    "You are given a general question or casual message that doesn't need real-time web "
    "data, file creation, code execution, or email drafting. "
    "Answer directly and conversationally from your own knowledge, in a few sentences."
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
def _call_llm(instruction: str) -> str:
    response = _client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ],
        temperature=0.5,
    )
    return response.choices[0].message.content


def run(instruction: str) -> str:
    try:
        answer = _call_llm(instruction)
        log_event("general_agent", "answer", instruction, answer, status="success")
        return answer
    except Exception as e:
        log_event("general_agent", "answer", instruction, str(e), status="error")
        raise
