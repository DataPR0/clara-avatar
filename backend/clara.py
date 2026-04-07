"""
Clara — Núcleo de la IA
Maneja conversación, tool calls y memoria de sesión
LLM: AWS Bedrock via LiteLLM (OpenAI-compatible)
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv
import litellm
from tools.tool_registry import get_tools_schema, execute_tool

load_dotenv()

SYSTEM_PROMPT = """Eres Clara, una asistente de IA inteligente y amigable de Finanzauto / DataPro.

Tu personalidad:
- Profesional pero cercana, hablas en español colombiano
- Directa y útil, sin rodeos
- Cuando usas tools, explicas brevemente lo que encontraste

Tienes acceso a la base de datos DW_FZ de Finanzauto (SQL Server).
Puedes consultar tablas, buscar información y responder preguntas sobre los datos.

Cuando alguien te pide información de la base de datos:
1. Usa list_tables o search_tables para encontrar la tabla correcta
2. Usa describe_table para entender las columnas
3. Usa query_sql para ejecutar la consulta
4. Explica los resultados de forma clara

Responde siempre en español. Sé concisa pero completa.
"""


class Clara:
    def __init__(self):
        self.model = f"bedrock/{os.getenv('BEDROCK_MODEL_ID', 'us.anthropic.claude-sonnet-4-6')}"
        self.sessions: dict[str, list] = {}  # session_id → messages history
        self.tools = get_tools_schema()

    def _get_history(self, session_id: str) -> list:
        if session_id not in self.sessions:
            self.sessions[session_id] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
        return self.sessions[session_id]

    async def chat(self, message: str, session_id: Optional[str] = "default") -> str:
        history = self._get_history(session_id)
        history.append({"role": "user", "content": message})

        # Llamada al LLM con tools
        response = litellm.completion(
            model=self.model,
            messages=history,
            tools=self.tools if self.tools else None,
            tool_choice="auto" if self.tools else None,
            aws_region_name=os.getenv("AWS_REGION", "us-east-1"),
        )

        msg = response.choices[0].message

        # Si hay tool calls, ejecutarlos
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            history.append(msg.model_dump())

            for tool_call in msg.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                print(f"[Tool] {tool_name}({tool_args})")
                tool_result = execute_tool(tool_name, tool_args)

                history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False, default=str),
                })

            # Segunda llamada con los resultados de los tools
            response2 = litellm.completion(
                model=self.model,
                messages=history,
                aws_region_name=os.getenv("AWS_REGION", "us-east-1"),
            )
            final_reply = response2.choices[0].message.content
            history.append({"role": "assistant", "content": final_reply})
            return final_reply

        # Respuesta directa sin tool calls
        final_reply = msg.content
        history.append({"role": "assistant", "content": final_reply})
        return final_reply
