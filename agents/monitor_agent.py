import os
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from tools.web_search import search_web
from memory.logger import log_event

_client = Groq(api_key=os.environ["GROQ_API_KEY"])

_SYSTEM_PROMPT = (
    "You are the Monitor Agent inside Jarvis, a multi-agent assistant. "
    "You are given a topic and a set of recent web search results about it. "
    "Summarize what is notable or newsworthy right now (3-6 sentences). "
    "If nothing significant stands out, say so plainly instead of inventing importance."
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
def _call_llm(topic: str, results: list[dict]) -> str:
    results_text = "\n\n".join(
        f"Title: {r['title']}\nSnippet: {r['snippet']}\nURL: {r['url']}" for r in results
    )
    response = _client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Topic: {topic}\n\nRecent search results:\n{results_text}"},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


def run(topic: str) -> str:
    try:
        results = search_web(topic, search_type="news", recent_days=7)
        log_event("monitor_agent", "tool_call", topic, str(results), status="success")
    except Exception as e:
        log_event("monitor_agent", "tool_call", topic, str(e), status="error")
        raise

    try:
        summary = _call_llm(topic, results)
        log_event("monitor_agent", "summary", topic, summary, status="success")
        return summary
    except Exception as e:
        log_event("monitor_agent", "summary", topic, str(e), status="error")
        raise
