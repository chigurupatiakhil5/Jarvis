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

CREATE TABLE IF NOT EXISTS preferences (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    description TEXT NOT NULL
);

ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE preferences ADD COLUMN IF NOT EXISTS user_id TEXT;
"""


def get_connection():
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ["POSTGRES_PORT"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
        sslmode="require",
    )


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_CREATE_TABLE_SQL)
        conn.commit()


def log_event(user_id: str, agent_name: str, action_type: str, input_text: str, output_text: str, status: str = "success"):
    timestamp = datetime.now(timezone.utc)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_logs (timestamp, agent_name, action_type, input, output, status, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (timestamp, agent_name, action_type, input_text, output_text, status, user_id),
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


def save_preference(user_id: str, description: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO preferences (timestamp, description, user_id) VALUES (%s, %s, %s)",
                (datetime.now(timezone.utc), description, user_id),
            )
        conn.commit()


def get_preferences(user_id: str) -> list[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT description FROM preferences WHERE user_id = %s ORDER BY id", (user_id,))
            return [row[0] for row in cur.fetchall()]


def get_recent_notifications(user_id: str, hours: int = 6) -> list[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT output FROM agent_logs
                WHERE agent_name = 'scheduler' AND action_type = 'notify'
                AND user_id = %s
                AND timestamp > NOW() - INTERVAL '%s hours'
                ORDER BY id
                """,
                (user_id, hours),
            )
            return [row[0] for row in cur.fetchall()]
