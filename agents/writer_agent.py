import os
import re
from datetime import datetime
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from tools.file_manager import save_document
from memory.logger import log_event

_client = Groq(api_key=os.environ["GROQ_API_KEY"])

_SYSTEM_PROMPT = (
    "You are the Writer Agent inside Jarvis, a multi-agent assistant. "
    "You are given an instruction and you write clear, well-structured content "
    "that fulfills it (a document, report, summary, etc.). "
    "Write only the requested content — no preamble like 'Here is your document'."
)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:50] or "document"


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


def run(user_id: str, instruction: str) -> str:
    try:
        content = _call_llm(instruction)
        log_event(user_id, "writer_agent", "generate", instruction, content, status="success")
    except Exception as e:
        log_event(user_id, "writer_agent", "generate", instruction, str(e), status="error")
        raise

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{timestamp}-{_slugify(instruction)}.md"

    try:
        path = save_document("documents", filename, content)
        log_event(user_id, "writer_agent", "save_file", filename, path, status="success")
    except Exception as e:
        log_event(user_id, "writer_agent", "save_file", filename, str(e), status="error")
        raise

    return f"{content}\n\n[saved to {path}]"
