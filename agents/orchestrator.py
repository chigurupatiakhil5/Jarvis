import os
import json
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_fixed

from agents import research_agent, writer_agent, email_agent, code_agent, monitor_agent
from memory.logger import log_event

_client = Groq(api_key=os.environ["GROQ_API_KEY"])

_AVAILABLE_AGENTS = {
    "research": "Searches the web and summarizes findings to answer a question.",
    "writer": "Writes documents, reports, or summaries and saves them to disk.",
    "email": "Drafts an email (subject + body) and saves it for review. Does not send or read real email.",
    "code": "Writes a Python script and runs it, returning the output.",
    "monitor": "Checks for recent news or developments on a topic, right now.",
}

_SYSTEM_PROMPT = (
    "You are the Orchestrator inside Jarvis, a multi-agent assistant. "
    f"The user gives you a command. Available agents:\n{json.dumps(_AVAILABLE_AGENTS, indent=2)}\n"
    "Decide which agent should handle the command, and rewrite the command as a clear, "
    "specific instruction for that agent. "
    'Respond with ONLY valid JSON in this exact shape: {"agent": "<agent name>", "instruction": "<rewritten instruction>"}'
)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def _plan(command: str) -> dict:
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
    try:
        plan = _plan(command)
        log_event("orchestrator", "plan", command, json.dumps(plan), status="success")
    except Exception as e:
        log_event("orchestrator", "plan", command, str(e), status="error")
        raise

    agent_name = plan.get("agent")
    instruction = plan.get("instruction", command)

    agent_modules = {
        "research": research_agent,
        "writer": writer_agent,
        "email": email_agent,
        "code": code_agent,
        "monitor": monitor_agent,
    }

    agent_module = agent_modules.get(agent_name)
    if agent_module is None:
        raise ValueError(f"Orchestrator chose unknown agent: {agent_name!r}")

    return agent_module.run(instruction)
