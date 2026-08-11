"""
A tool: a plain function that acts on the real world.
Searches the web via Tavily — a search API built for AI agents.
Free tier: 1,000 searches/month. Requires a free API key (TAVILY_API_KEY in .env).
"""

import os
from typing import Optional
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential

_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
def search_web(query: str, max_results: int = 5, search_type: str = "general", recent_days: Optional[int] = None) -> list[dict]:
    """
    Search the web and return a list of {title, snippet, url} dicts.
    Retries up to 3 times with exponential backoff if the request fails.

    search_type: "general" (default) or "news" — Tavily's built-in recency-biased
    search mode. Use "news" instead of hand-writing "latest"/"recent" into the
    query text, which produces noisy, badly-parsed searches.
    recent_days: when search_type="news", restrict results to the last N days.
    """
    kwargs = {"max_results": max_results, "topic": search_type}
    if search_type == "news" and recent_days:
        kwargs["days"] = recent_days

    response = _client.search(query, **kwargs)
    return [
        {
            "title": r.get("title", ""),
            "snippet": r.get("content", ""),
            "url": r.get("url", ""),
        }
        for r in response.get("results", [])
    ]
