"""
LiveAvatar Client
Maneja sesiones FULL Mode con LLM Bedrock + ElevenLabs TTS
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

LIVEAVATAR_API_KEY = os.getenv("LIVEAVATAR_API_KEY", "")
LIVEAVATAR_BASE = "https://api.liveavatar.com"
LIVEAVATAR_AVATAR_ID = os.getenv("LIVEAVATAR_AVATAR_ID", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")


class LiveAvatarClient:
    def __init__(self):
        self.headers = {
            "X-API-KEY": LIVEAVATAR_API_KEY,
            "Content-Type": "application/json",
        }
        self._elevenlabs_secret_id = None
        self._elevenlabs_voice_id_la = None  # voice_id dentro de LiveAvatar
        self._llm_config_id = None

    async def _ensure_secrets(self):
        """Registra ElevenLabs secret si no existe aún."""
        if self._elevenlabs_secret_id:
            return

        async with httpx.AsyncClient() as client:
            # Registrar ElevenLabs API key
            r = await client.post(
                f"{LIVEAVATAR_BASE}/v1/secrets",
                headers=self.headers,
                json={
                    "secret_type": "ELEVENLABS_API_KEY",
                    "secret_value": ELEVENLABS_API_KEY,
                    "secret_name": "ElevenLabs Clara",
                },
            )
            r.raise_for_status()
            self._elevenlabs_secret_id = r.json()["data"]["secret_id"]

            # Importar la voz de ElevenLabs a LiveAvatar
            r2 = await client.post(
                f"{LIVEAVATAR_BASE}/v1/voices/third_party",
                headers=self.headers,
                json={
                    "secret_id": self._elevenlabs_secret_id,
                    "voice_id": ELEVENLABS_VOICE_ID,
                },
            )
            r2.raise_for_status()
            self._elevenlabs_voice_id_la = r2.json()["data"]["voice_id"]

    async def _ensure_llm_config(self, bedrock_proxy_url: str, bedrock_api_key: str):
        """Registra configuración LLM Bedrock si no existe."""
        if self._llm_config_id:
            return

        async with httpx.AsyncClient() as client:
            # Registrar API key del proxy Bedrock
            r = await client.post(
                f"{LIVEAVATAR_BASE}/v1/secrets",
                headers=self.headers,
                json={
                    "secret_type": "LLM_API_KEY",
                    "secret_value": bedrock_api_key,
                    "secret_name": "Bedrock LiteLLM Proxy",
                },
            )
            r.raise_for_status()
            llm_secret_id = r.json()["data"]["secret_id"]

            # Crear configuración LLM apuntando al proxy LiteLLM
            r2 = await client.post(
                f"{LIVEAVATAR_BASE}/v1/llm_configurations",
                headers=self.headers,
                json={
                    "display_name": "Bedrock Claude via LiteLLM",
                    "model_name": "gpt-4o",  # nombre que ve LiveAvatar (proxy lo mapea a Bedrock)
                    "secret_id": llm_secret_id,
                    "base_url": bedrock_proxy_url,
                },
            )
            r2.raise_for_status()
            self._llm_config_id = r2.json()["data"]["llm_configuration_id"]

    async def create_embed(self, avatar_id: str = None, sandbox: bool = False) -> dict:
        """Crea un embed LiveAvatar y retorna URL del iframe."""
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

    async def start_full_session(self, avatar_id: str = None) -> dict:
        """Inicia sesión FULL Mode con ElevenLabs + contexto de Clara."""
        await self._ensure_secrets()

        async with httpx.AsyncClient() as client:
            # Crear token de sesión
            r = await client.post(
                f"{LIVEAVATAR_BASE}/v1/sessions/token",
                headers=self.headers,
                json={
                    "mode": "FULL",
                    "avatar_id": avatar_id or LIVEAVATAR_AVATAR_ID,
                    "avatar_persona": {
                        "voice_id": self._elevenlabs_voice_id_la,
                    },
                },
            )
            r.raise_for_status()
            return r.json()["data"]

    async def stop_session(self, session_id: str) -> dict:
        """Detiene una sesión activa."""
        async with httpx.AsyncClient() as client:
            r = await client.delete(
                f"{LIVEAVATAR_BASE}/v1/sessions/{session_id}",
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()

    async def list_avatars(self) -> list:
        """Lista avatares disponibles."""
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{LIVEAVATAR_BASE}/v1/avatars",
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()["data"]
