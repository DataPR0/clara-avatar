# 🎙️ Clara — AI Avatar

> "Oye Clara" → Clara te escucha, piensa y responde con voz y video en tiempo real.

Clara es una asistente de IA con cara, voz y cerebro:

- 🧠 **LLM:** AWS Bedrock (Claude Sonnet)
- 🎤 **TTS:** ElevenLabs (voz personalizada)
- 🎥 **Avatar video:** LiveAvatar (HeyGen)
- 🗄️ **Tools:** Consultas a SQL Server (`192.168.50.38\DW_FZ`)
- 🔊 **Wake word:** "Oye Clara" (detección local con Porcupine/Vosk)

---

## Arquitectura

```
[Micrófono] → Wake Word "Oye Clara"
    ↓
[STT — Whisper/Browser API]
    ↓
[Backend FastAPI]
    ├── LLM: AWS Bedrock (Claude Sonnet via OpenAI-compat proxy)
    ├── Tools: SQL Server DW_FZ
    └── TTS: ElevenLabs
    ↓
[LiveAvatar FULL Mode] → Video avatar hablando en el browser
```

---

## Stack

| Componente | Tecnología |
|---|---|
| Backend | Python + FastAPI |
| LLM | AWS Bedrock (Claude Sonnet) — via LiteLLM proxy |
| TTS | ElevenLabs API |
| Avatar Video | LiveAvatar FULL Mode (HeyGen) |
| Wake Word | Porcupine (Picovoice) o Vosk offline |
| STT | Web Speech API (browser) o Whisper |
| DB | SQL Server `192.168.50.38\DW_FZ` via pyodbc |
| Frontend | HTML + Vanilla JS (iframe LiveAvatar) |

---

## Setup rápido

```bash
# 1. Instalar dependencias
cd backend
pip install -r requirements.txt

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# 3. Levantar backend
uvicorn main:app --reload --port 8090

# 4. Abrir frontend
open ../frontend/index.html
```

---

## Variables de entorno

Ver [`.env.example`](backend/.env.example)

---

## Tools disponibles

| Tool | Descripción |
|---|---|
| `query_sql` | Ejecuta SELECT en DW_FZ y retorna resultados |
| `list_tables` | Lista todas las tablas disponibles |
| `describe_table` | Muestra columnas y tipos de una tabla |
| `search_tables` | Busca tablas por nombre o descripción |

---

## Estructura

```
clara-avatar/
├── backend/
│   ├── main.py              # FastAPI app + LiteLLM proxy
│   ├── clara.py             # Lógica principal de Clara
│   ├── tools/
│   │   ├── sql_tools.py     # Consultas SQL Server
│   │   └── tool_registry.py # Registro de tools
│   ├── liveavatar.py        # Cliente LiveAvatar API
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html           # App principal
│   └── src/
│       ├── app.js           # Wake word + STT + LiveAvatar embed
│       └── style.css
├── tools/                   # Tools adicionales (extensible)
└── docs/
    └── sql-context.md       # Contexto de tablas DW_FZ
```
