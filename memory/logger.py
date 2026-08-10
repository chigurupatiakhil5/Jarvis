"""
Talks to PostgreSQL. This is the only file in the project that runs SQL.
Every agent decision and tool call gets written here with a timestamp,
so the full history of what May did is always inspectable later.
"""

import os
import psycopg2
from datetime import datetime, timezone

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS agent_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    agent_name TEXT NOT NULL,
    action_type TEXT NOT NULL,
    input TEXT,
    output TEXT,
    status TEXT NOT NULL
);
"""


def get_connection():
    """Open a new connection to Postgres using settings from .env."""
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )


def init_db():
    """Create the agent_logs table if it doesn't exist yet. Safe to call every startup."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_CREATE_TABLE_SQL)
        conn.commit()


def log_event(agent_name: str, action_type: str, input_text: str, output_text: str, status: str = "success"):
    """
    Write one row to agent_logs.

    agent_name:  who did this ("orchestrator", "research_agent", ...)
    action_type: what kind of step this was ("plan", "tool_call", "summary", ...)
    input_text:  what went into this step
    output_text: what came out of this step
    status:      "success" or "error"
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_logs (timestamp, agent_name, action_type, input, output, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (datetime.now(timezone.utc), agent_name, action_type, input_text, output_text, status),
            )
        conn.commit()
