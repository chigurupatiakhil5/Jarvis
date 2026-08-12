from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from memory.logger import get_connection

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_connections: list[WebSocket] = []


class AgentEvent(BaseModel):
    agent_name: str
    action_type: str
    input: str
    output: str
    status: str
    timestamp: str


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _connections.remove(websocket)


@app.post("/events")
async def receive_event(event: AgentEvent):
    dead = []
    for ws in _connections:
        try:
            await ws.send_json(event.model_dump())
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.remove(ws)
    return {"ok": True}


@app.get("/logs")
def get_recent_logs(limit: int = 50):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT agent_name, action_type, input, output, status, timestamp "
                "FROM agent_logs ORDER BY id DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
    return [
        {
            "agent_name": r[0],
            "action_type": r[1],
            "input": r[2],
            "output": r[3],
            "status": r[4],
            "timestamp": r[5].isoformat(),
        }
        for r in reversed(rows)
    ]
