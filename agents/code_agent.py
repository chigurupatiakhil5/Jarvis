import os
import re
import subprocess
from datetime import datetime
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from tools.file_manager import save_document
from memory.logger import log_event

_client = Groq(api_key=os.environ["GROQ_API_KEY"])
_EXECUTION_TIMEOUT_SECONDS = 10

_SYSTEM_PROMPT = (
    "You are the Code Agent inside May, a multi-agent assistant. "
    "You are given an instruction describing a small Python program to write. "
    "Write ONLY the Python code that fulfills it — no markdown code fences, no explanation. "
    "The code should print its result so the output is visible when run."
)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:50] or "script"


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:python)?\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
def _call_llm(instruction: str) -> str:
    response = _client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ],
        temperature=0.2,
    )
    return _strip_code_fences(response.choices[0].message.content)


def run(instruction: str) -> str:
    try:
        code = _call_llm(instruction)
        log_event("code_agent", "generate", instruction, code, status="success")
    except Exception as e:
        log_event("code_agent", "generate", instruction, str(e), status="error")
        raise

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{timestamp}-{_slugify(instruction)}.py"
    path = save_document("code", filename, code)
    log_event("code_agent", "save_file", filename, path, status="success")

    try:
        result = subprocess.run(
            ["python3", path],
            capture_output=True,
            text=True,
            timeout=_EXECUTION_TIMEOUT_SECONDS,
        )
        output = result.stdout if result.returncode == 0 else f"Error:\n{result.stderr}"
        status = "success" if result.returncode == 0 else "error"
        log_event("code_agent", "execute", path, output, status=status)
    except subprocess.TimeoutExpired:
        output = f"Execution timed out after {_EXECUTION_TIMEOUT_SECONDS}s"
        log_event("code_agent", "execute", path, output, status="error")

    return f"Code saved to {path}\n\n```python\n{code}\n```\n\nOutput:\n{output}"
