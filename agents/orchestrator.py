"""
Orchestrator: the "chief of staff" agent.
Reads the user's raw command, decides which worker agent should handle it,
and hands off the work. In v0, Research is the only available worker.
"""

import os
import json
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_fixed

from agents import research_agent
from memory.logger import log_event

_client = Groq(api_key=os.environ["GROQ_API_KEY"])

# Only "research" exists in v0. More agents get added to this dict in v1 —
# the orchestrator's routing logic below doesn't need to change to support that.
_AVAILABLE_AGENTS = ["research"]

_SYSTEM_PROMPT = (
    "You are the Orchestrator inside May, a multi-agent assistant. "
    f"The user gives you a command. Available agents: {_AVAILABLE_AGENTS}. "
    "Decide which agent should handle the command, and rewrite the command as a clear, "
    "specific instruction for that agent. "
    'Respond with ONLY valid JSON in this exact shape: {"agent": "<agent name>", "instruction": "<rewritten instruction>"}'
)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def _plan(command: str) -> dict:
    """Ask Groq/LLaMA 3 which agent should handle this command. Retries on API failure."""
    response = _client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": command},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def handle_command(command: str) -> str:
    """
    Full Orchestrator flow: plan, log the decision, delegate to the chosen agent.
    """
    try:
        plan = _plan(command)
        log_event("orchestrator", "plan", command, json.dumps(plan), status="success")
    except Exception as e:
        log_event("orchestrator", "plan", command, str(e), status="error")
        raise

    agent_name = plan.get("agent")
    instruction = plan.get("instruction", command)

    if agent_name == "research":
        return research_agent.run(instruction)

    # Should not happen in v0 since "research" is the only option the LLM was given,
    # but if the model ever returns something unexpected, fail loudly instead of guessing.
    raise ValueError(f"Orchestrator chose unknown agent: {agent_name!r}")
