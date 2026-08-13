import base64
import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from memory.logger import get_connection
from agents.orchestrator import handle_command
from voice.speech_to_text import transcribe_audio_file
from voice.text_to_speech import synthesize_bytes

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


@app.post("/chat/audio")
async def chat_audio(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    suffix = os.path.splitext(file.filename or "")[1] or ".webm"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio_bytes)
        temp_path = f.name

    try:
        transcript = transcribe_audio_file(temp_path)
    finally:
        os.remove(temp_path)

    if not transcript:
        return {"transcript": "", "response_text": "I didn't catch that — could you try again?", "response_audio_base64": None}

    try:
        response_text = handle_command(transcript)
    except Exception as e:
        response_text = f"Something went wrong: {e}"

    audio_bytes_out = synthesize_bytes(response_text)
    response_audio_base64 = base64.b64encode(audio_bytes_out).decode() if audio_bytes_out else None

    return {
        "transcript": transcript,
        "response_text": response_text,
        "response_audio_base64": response_audio_base64,
    }


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
