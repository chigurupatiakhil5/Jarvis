"""
A tool: a plain function that acts on the real world.
Searches the web via Tavily — a search API built for AI agents.
Free tier: 1,000 searches/month. Requires a free API key (TAVILY_API_KEY in .env).
"""

import os
from tavily import TavilyClient
from tenacity import retry, stop_after_attempt, wait_exponential

_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web and return a list of {title, snippet, url} dicts.
    Retries up to 3 times with exponential backoff if the request fails.
    """
    response = _client.search(query, max_results=max_results)
    return [
        {
            "title": r.get("title", ""),
            "snippet": r.get("content", ""),
            "url": r.get("url", ""),
        }
        for r in response.get("results", [])
    ]
