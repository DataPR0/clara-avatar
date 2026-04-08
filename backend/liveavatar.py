"""
LiveAvatar Client — LITE Mode
Maneja sesiones donde nosotros traemos el LLM + TTS y LiveAvatar solo renderiza el video.

Flujo LITE:
  1. POST /v1/sessions/token  (mode=LITE)  → session_token
  2. POST /v1/sessions/start              → livekit_url + livekit_client_token + websocket_url + session_id
  3. Frontend conecta LiveKit  (recibe video del avatar)
  4. Backend conecta WebSocket (envía audio PCM 16bit 24KHz en chunks base64)
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

LIVEAVATAR_API_KEY    = os.getenv("LIVEAVATAR_API_KEY", "")
LIVEAVATAR_BASE       = "https://api.liveavatar.com"
LIVEAVATAR_AVATAR_ID  = os.getenv("LIVEAVATAR_AVATAR_ID",  "de82b2cc-7314-40a1-b41f-cc456c66601c")


class LiveAvatarClient:
    def __init__(self):
        self.headers = {
            "X-API-KEY": LIVEAVATAR_API_KEY,
            "Content-Type": "application/json",
        }

    # ── Token ──────────────────────────────────────────────────────────────────

    async def create_session_token(self) -> dict:
        """Crea un session token LITE Mode. Solo necesita avatar_id."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{LIVEAVATAR_BASE}/v1/sessions/token",
                headers=self.headers,
                json={
                    "mode": "LITE",
                    "avatar_id": LIVEAVATAR_AVATAR_ID,
                },
            )
            r.raise_for_status()
            return r.json()["data"]

    # ── Start ──────────────────────────────────────────────────────────────────

    async def start_session(self, session_token: str) -> dict:
        """
        Inicia la sesión LITE.
        Retorna: { session_id, livekit_url, livekit_client_token, websocket_url }
        """
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{LIVEAVATAR_BASE}/v1/sessions/start",
                headers={
                    "Authorization": f"Bearer {session_token}",
                    "Content-Type": "application/json",
                },
            )
            r.raise_for_status()
            return r.json()["data"]

    # ── Stop ───────────────────────────────────────────────────────────────────

    async def stop_session(self, session_id: str) -> dict:
        """Detiene una sesión activa."""
        async with httpx.AsyncClient() as client:
            r = await client.delete(
                f"{LIVEAVATAR_BASE}/v1/sessions/{session_id}",
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    # ── Embed (fallback) ───────────────────────────────────────────────────────

    async def create_embed(self, avatar_id: str = None, sandbox: bool = False) -> dict:
        """Crea un embed iframe (fallback si LITE no está disponible)."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{LIVEAVATAR_BASE}/v2/embeddings",
                headers=self.headers,
                json={
                    "avatar_id": avatar_id or LIVEAVATAR_AVATAR_ID,
                    "is_sandbox": sandbox,
                },
            )
            r.raise_for_status()
            return r.json()["data"]
