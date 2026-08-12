import os
import psycopg2
import httpx
from datetime import datetime, timezone

_EVENTS_URL = "http://localhost:8001/events"

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
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_CREATE_TABLE_SQL)
        conn.commit()


def log_event(agent_name: str, action_type: str, input_text: str, output_text: str, status: str = "success"):
    timestamp = datetime.now(timezone.utc)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_logs (timestamp, agent_name, action_type, input, output, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (timestamp, agent_name, action_type, input_text, output_text, status),
            )
        conn.commit()

    try:
        httpx.post(
            _EVENTS_URL,
            json={
                "agent_name": agent_name,
                "action_type": action_type,
                "input": input_text,
                "output": output_text,
                "status": status,
                "timestamp": timestamp.isoformat(),
            },
            timeout=1.0,
        )
    except Exception:
        pass
