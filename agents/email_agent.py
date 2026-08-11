import os
import json
import re
from datetime import datetime
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from tools.file_manager import save_document
from memory.logger import log_event

_client = Groq(api_key=os.environ["GROQ_API_KEY"])

_SYSTEM_PROMPT = (
    "You are the Email Agent inside May, a multi-agent assistant. "
    "You are given an instruction describing an email to draft. "
    "Write a professional subject line and body. "
    'Respond with ONLY valid JSON in this exact shape: {"subject": "<subject>", "body": "<body>"}'
)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:50] or "email"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
def _call_llm(instruction: str) -> dict:
    response = _client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def run(instruction: str) -> str:
    try:
        draft = _call_llm(instruction)
        log_event("email_agent", "draft", instruction, json.dumps(draft), status="success")
    except Exception as e:
        log_event("email_agent", "draft", instruction, str(e), status="error")
        raise

    subject = draft.get("subject", "(no subject)")
    body = draft.get("body", "")
    formatted = f"Subject: {subject}\n\n{body}"

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{timestamp}-{_slugify(subject)}.txt"

    try:
        path = save_document("drafts", filename, formatted)
        log_event("email_agent", "save_file", filename, path, status="success")
    except Exception as e:
        log_event("email_agent", "save_file", filename, str(e), status="error")
        raise

    return f"{formatted}\n\n[draft saved to {path} — review before sending]"
