"""
Clara — Backend principal (LITE Mode)
FastAPI app con LLM Bedrock, Tools SQL Server, LiveAvatar LITE Mode

Flujo LITE:
  POST /session/token  → { session_token, session_id }
  POST /session/start  → { session_id, livekit_url, livekit_client_token, websocket_url }
  POST /chat/speak     → recibe texto, llama ElevenLabs, envía audio PCM por WS a LiveAvatar
  DELETE /session/{id} → cierra sesión
"""

import os
import json
import base64
import asyncio
import httpx
import websockets
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional

from clara import Clara
from liveavatar import LiveAvatarClient

load_dotenv()

app = FastAPI(title="Clara Avatar API — LITE Mode", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clara = Clara()
liveavatar = LiveAvatarClient()

# Mapa de sesiones activas: session_id → websocket_url
active_sessions: dict[str, str] = {}


# ─── Models ───────────────────────────────────────────────────────────────────

class ChatSpeakRequest(BaseModel):
    message: str
    session_id: str
    backend_session_id: Optional[str] = None  # para historial de chat


class StartRequest(BaseModel):
    session_token: str


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "name": "Clara", "mode": "LITE"}


# ─── Session lifecycle ────────────────────────────────────────────────────────

@app.post("/session/token")
async def get_session_token():
    """Crea un session token LITE Mode."""
    try:
        data = await liveavatar.create_session_token()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/start")
async def start_session(req: StartRequest):
    """
    Inicia la sesión LITE.
    Retorna: livekit_url, livekit_client_token, websocket_url, session_id
    """
    try:
        data = await liveavatar.start_session(req.session_token)
        session_id = data.get("session_id")
        ws_url = data.get("ws_url") or data.get("websocket_url")
        if session_id and ws_url:
            active_sessions[session_id] = ws_url
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/session/{session_id}")
async def stop_session(session_id: str):
    """Detiene una sesión activa."""
    try:
        active_sessions.pop(session_id, None)
        result = await liveavatar.stop_session(session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Chat + Speak ─────────────────────────────────────────────────────────────

@app.post("/chat/speak")
async def chat_and_speak(req: ChatSpeakRequest):
    """
    Flujo completo LITE Mode:
    1. Envía mensaje a Clara (Bedrock LLM)
    2. Convierte respuesta a audio PCM con ElevenLabs
    3. Envía chunks de audio al WebSocket de LiveAvatar
    4. Avatar habla en tiempo real
    """
    # 1. LLM
    try:
        reply = await clara.chat(req.message, session_id=req.backend_session_id or req.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    # 2. TTS → PCM 16bit 24KHz
    try:
        pcm_audio = await text_to_pcm(reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {e}")

    # 3. Enviar audio al avatar por WebSocket
    ws_url = active_sessions.get(req.session_id)
    if ws_url:
        try:
            await send_audio_to_avatar(ws_url, pcm_audio)
        except Exception as e:
            # No falla el endpoint si el WS falla — la respuesta de texto ya está
            print(f"[WS] Error enviando audio: {e}")

    return {"reply": reply, "session_id": req.session_id}


async def text_to_pcm(text: str) -> bytes:
    """
    ElevenLabs TTS → PCM 16bit 24KHz (formato requerido por LiveAvatar LITE).
    Usa output_format=pcm_24000.
    """
    voice_id = os.getenv("LIVEAVATAR_VOICE_ID") or os.getenv("ELEVENLABS_VOICE_ID", "fd41bfa4-8632-4946-8f5e-d6c9cc1da67b")
    api_key  = os.getenv("ELEVENLABS_API_KEY", os.getenv("LIVEAVATAR_ELEVENLABS_SECRET_ID", ""))

    # Intentar con la API key de ElevenLabs directa
    eleven_key = os.getenv("ELEVENLABS_API_KEY", "")
    if not eleven_key:
        # Fallback: usar la key guardada en MEMORY para Felipe FZ
        eleven_key = "sk_e61853d9dab29ca137fee5b41905cfd3fde3d46cee48e0a0"

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": eleven_key,
                "Content-Type": "application/json",
            },
            params={"output_format": "pcm_24000"},
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                },
            },
        )
        r.raise_for_status()
        return r.content


async def send_audio_to_avatar(ws_url: str, pcm_audio: bytes):
    """
    Envía audio PCM al avatar vía WebSocket LiveAvatar LITE.
    Protocolo:
      - agent.start_listening (opcional, pone avatar en pose escucha)
      - agent.speak  { audio: <base64 PCM chunk ~1s> }  x N chunks
      - agent.speak_end { event_id }
    """
    import uuid

    # Dividir audio en chunks de ~1s (24000 samples * 2 bytes = 48000 bytes/s)
    CHUNK_SIZE = 48000  # ~1 segundo a 24KHz 16bit mono
    chunks = [pcm_audio[i:i+CHUNK_SIZE] for i in range(0, len(pcm_audio), CHUNK_SIZE)]
    event_id = str(uuid.uuid4())

    async with websockets.connect(ws_url) as ws:
        # Esperar confirmación de conexión
        connected = False
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(msg)
            if data.get("state") == "connected" or data.get("type") == "session.state_updated":
                connected = True
        except asyncio.TimeoutError:
            connected = True  # Asumir conectado si no hay respuesta inicial

        # Enviar chunks de audio
        for chunk in chunks:
            audio_b64 = base64.b64encode(chunk).decode("utf-8")
            await ws.send(json.dumps({
                "type": "agent.speak",
                "audio": audio_b64,
            }))
            await asyncio.sleep(0.05)  # pequeño delay entre chunks

        # Señal de fin
        await ws.send(json.dumps({
            "type": "agent.speak_end",
            "event_id": event_id,
        }))


# ─── Chat solo texto (sin avatar) ────────────────────────────────────────────

@app.post("/chat")
async def chat_text_only(request: Request):
    """Chat solo texto — sin avatar. Para pruebas o fallback."""
    body = await request.json()
    message = body.get("message", "")
    session_id = body.get("session_id", "default")
    try:
        reply = await clara.chat(message, session_id=session_id)
        return {"reply": reply, "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Tools info ───────────────────────────────────────────────────────────────

@app.get("/tools")
async def list_tools():
    from tools.tool_registry import get_tools_schema
    return {"tools": get_tools_schema()}


# ─── SQL ──────────────────────────────────────────────────────────────────────

@app.get("/sql/tables")
async def list_tables():
    from tools.sql_tools import SqlTools
    sql = SqlTools()
    return {"tables": sql.list_tables()}


@app.get("/sql/describe/{table_name}")
async def describe_table(table_name: str):
    from tools.sql_tools import SqlTools
    sql = SqlTools()
    return {"table": table_name, "columns": sql.describe_table(table_name)}


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", 8090))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
