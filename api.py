import base64
import os
import tempfile
import jwt
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from memory.logger import get_connection, init_db
from agents.orchestrator import handle_command
from voice.speech_to_text import transcribe_audio_file
from voice.text_to_speech import synthesize_bytes

init_db()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_connections: list[WebSocket] = []

_jwks_client = jwt.PyJWKClient(f"{os.environ['SUPABASE_URL']}/auth/v1/.well-known/jwks.json")


def require_user(authorization: str = Header(None)) -> str:
    """
    FastAPI dependency: verifies the Supabase-issued access token in the
    Authorization header and returns the caller's user ID (the token's
    "sub" claim). Signature is checked against Supabase's public signing
    key (fetched and cached from their JWKS endpoint) so a request can't
    fake being a different user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()

    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(token, signing_key.key, algorithms=["ES256"], audience="authenticated")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    return payload["sub"]


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
async def chat_audio(file: UploadFile = File(...), user_id: str = Depends(require_user)):
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
        response_text = handle_command(user_id, transcript)
    except Exception as e:
        response_text = f"Something went wrong: {e}"

    audio_bytes_out, audio_mime_type = synthesize_bytes(response_text)
    response_audio_base64 = base64.b64encode(audio_bytes_out).decode() if audio_bytes_out else None

    return {
        "transcript": transcript,
        "response_text": response_text,
        "response_audio_base64": response_audio_base64,
        "response_audio_mime_type": audio_mime_type,
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
