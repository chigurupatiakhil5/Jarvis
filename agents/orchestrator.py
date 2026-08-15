import os
import json
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_fixed

from agents import research_agent, writer_agent, email_agent, code_agent, monitor_agent, preferences_agent, general_agent
from memory.logger import log_event, get_preferences

_client = Groq(api_key=os.environ["GROQ_API_KEY"])

_AVAILABLE_AGENTS = {
    "research": "Searches the web for CURRENT or real-time information (news, recent events, things that change over time) and summarizes findings.",
    "writer": "Writes documents, reports, or summaries and saves them to disk.",
    "email": "Drafts an email (subject + body) and saves it for review. Does not send or read real email.",
    "code": "Writes a Python script and runs it, returning the output.",
    "monitor": "Checks for recent news or developments on a topic, right now, as a single one-off lookup. Never use this for 'notify me when/during X' or any recurring/future notification request — that's the background scheduler's job, triggered by saving a preference instead.",
    "preferences": "Saves a NEW thing the user tells you they like, want, or care about, OR any request to be notified/reminded about something recurring or ongoing (e.g. 'notify me during sunset every day', 'tell me when it rains') — these get saved as a preference for the background scheduler to act on later, not looked up immediately. Only for statements introducing new information — never for questions asking what's already been saved.",
    "general": "Answers general knowledge questions, casual conversation, questions about what the user has already told Jarvis they like/prefer (e.g. 'what do I like', 'what have I told you about me'), or anything answerable from the model's own knowledge WITHOUT needing current/real-time web data.",
}


def _build_system_prompt(user_id: str) -> str:
    preferences = get_preferences(user_id)
    preferences_block = "\n".join(f"- {p}" for p in preferences) if preferences else "(none yet)"
    return (
        "You are the Orchestrator inside Jarvis, a multi-agent assistant. "
        f"The user gives you a command. Available agents:\n{json.dumps(_AVAILABLE_AGENTS, indent=2)}\n"
        f"Known user preferences (use these to personalize the instruction you write, when relevant):\n{preferences_block}\n"
        "Decide which agent should handle the command, and rewrite the command as a clear, "
        "specific instruction for that agent, folding in relevant preferences naturally. "
        'Respond with ONLY valid JSON in this exact shape: {"agent": "<agent name>", "instruction": "<rewritten instruction>"}'
    )


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def _plan(user_id: str, command: str) -> dict:
    response = _client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _build_system_prompt(user_id)},
            {"role": "user", "content": command},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def handle_command(user_id: str, command: str) -> str:
    try:
        plan = _plan(user_id, command)
        log_event(user_id, "orchestrator", "plan", command, json.dumps(plan), status="success")
    except Exception as e:
        log_event(user_id, "orchestrator", "plan", command, str(e), status="error")
        raise

    agent_name = plan.get("agent")
    instruction = plan.get("instruction", command)

    agent_modules = {
        "research": research_agent,
        "writer": writer_agent,
        "email": email_agent,
        "code": code_agent,
        "monitor": monitor_agent,
        "preferences": preferences_agent,
        "general": general_agent,
    }

    agent_module = agent_modules.get(agent_name)
    if agent_module is None:
        raise ValueError(f"Orchestrator chose unknown agent: {agent_name!r}")

    # The General agent handles open-ended chat, where the rewritten
    # instruction can strip out tone/specific wording that matters (e.g.
    # "thank you" becoming a generic "respond with a greeting"). It already
    # has direct access to saved preferences itself, so it doesn't need the
    # paraphrase — pass what the user actually said instead.
    if agent_name == "general":
        return agent_module.run(user_id, command)

    return agent_module.run(user_id, instruction)
