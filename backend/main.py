"""
Clara — Backend principal
FastAPI app con LLM Bedrock, Tools SQL Server, LiveAvatar FULL Mode
"""

import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional

from clara import Clara
from liveavatar import LiveAvatarClient

load_dotenv()

app = FastAPI(title="Clara Avatar API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clara = Clara()
liveavatar = LiveAvatarClient()


# ─── Models ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: bool = False


class EmbedRequest(BaseModel):
    avatar_id: Optional[str] = None
    sandbox: bool = False


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "name": "Clara"}


@app.post("/chat")
async def chat(req: ChatRequest):
    """Envía un mensaje a Clara y recibe respuesta con tool calls si aplica."""
    try:
        response = await clara.chat(req.message, session_id=req.session_id)
        return {"reply": response, "session_id": req.session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/embed")
async def create_embed(req: EmbedRequest):
    """Crea una sesión embed de LiveAvatar y retorna la URL del iframe."""
    try:
        embed = await liveavatar.create_embed(
            avatar_id=req.avatar_id,
            sandbox=req.sandbox
        )
        return embed
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/start")
async def start_session(req: EmbedRequest):
    """Inicia una sesión LiveAvatar FULL Mode con LLM Bedrock + ElevenLabs."""
    try:
        session = await liveavatar.start_full_session(
            avatar_id=req.avatar_id,
        )
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/session/{session_id}")
async def stop_session(session_id: str):
    """Detiene una sesión LiveAvatar activa."""
    try:
        result = await liveavatar.stop_session(session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools")
async def list_tools():
    """Lista los tools disponibles para Clara."""
    from tools.tool_registry import get_tools_schema
    return {"tools": get_tools_schema()}


@app.get("/sql/tables")
async def list_tables():
    """Lista todas las tablas de DW_FZ."""
    from tools.sql_tools import SqlTools
    sql = SqlTools()
    tables = sql.list_tables()
    return {"tables": tables}


@app.get("/sql/describe/{table_name}")
async def describe_table(table_name: str):
    """Describe las columnas de una tabla."""
    from tools.sql_tools import SqlTools
    sql = SqlTools()
    schema = sql.describe_table(table_name)
    return {"table": table_name, "columns": schema}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", 8090))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
