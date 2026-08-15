import os
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_fixed

from tools.web_search import search_web
from memory.logger import log_event

_client = Groq(api_key=os.environ["GROQ_API_KEY"])

_SYSTEM_PROMPT = (
    "You are the Research Agent inside Jarvis, a multi-agent assistant. "
    "You are given a user's question and a set of raw web search results. "
    "Write a clear, concise summary (3-6 sentences) that directly answers the question, "
    "based only on the search results provided. Do not make up information."
)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def _call_llm(query: str, results: list[dict]) -> str:
    results_text = "\n\n".join(
        f"Title: {r['title']}\nSnippet: {r['snippet']}\nURL: {r['url']}" for r in results
    )
    response = _client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {query}\n\nSearch results:\n{results_text}"},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


def run(user_id: str, query: str) -> str:
    try:
        results = search_web(query)
        log_event(user_id, "research_agent", "tool_call", query, str(results), status="success")
    except Exception as e:
        log_event(user_id, "research_agent", "tool_call", query, str(e), status="error")
        raise

    try:
        summary = _call_llm(query, results)
        log_event(user_id, "research_agent", "summary", query, summary, status="success")
        return summary
    except Exception as e:
        log_event(user_id, "research_agent", "summary", query, str(e), status="error")
        raise
