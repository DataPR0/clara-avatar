"""
Tool Registry — Registro de tools disponibles para Clara
Formato compatible con OpenAI function calling
"""

from tools.sql_tools import SqlTools

_sql = None

def _get_sql():
    global _sql
    if _sql is None:
        _sql = SqlTools()
    return _sql



TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_sql",
            "description": (
                "Ejecuta una consulta SELECT en la base de datos DW_FZ de Finanzauto (SQL Server). "
                "Úsala para obtener datos específicos. Solo permite SELECT."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "La consulta SQL SELECT a ejecutar. Ejemplo: SELECT TOP 10 * FROM dbo.MiTabla",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Número máximo de filas a retornar (default 100)",
                        "default": 100,
                    },
                },
                "required": ["sql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": (
                "Lista todas las tablas y vistas disponibles en la base de datos DW_FZ. "
                "Úsala primero cuando no sabes qué tablas existen."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_table",
            "description": (
                "Muestra las columnas, tipos de datos y propiedades de una tabla específica. "
                "Úsala para entender la estructura antes de hacer una consulta."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Nombre de la tabla, puede incluir schema. Ejemplo: dbo.Clientes o Clientes",
                    }
                },
                "required": ["table_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_tables",
            "description": (
                "Busca tablas en la base de datos cuyo nombre contiene una palabra clave. "
                "Úsala cuando no recuerdas el nombre exacto de una tabla."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Palabra clave para buscar en nombres de tablas. Ejemplo: 'credito', 'cliente', 'cartera'",
                    }
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_row_count",
            "description": "Retorna cuántas filas tiene una tabla.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Nombre de la tabla (con schema si aplica). Ejemplo: dbo.Creditos",
                    }
                },
                "required": ["table_name"],
            },
        },
    },
]


def get_tools_schema() -> list:
    return TOOLS


def execute_tool(tool_name: str, args: dict) -> any:
    """Ejecuta un tool por nombre y retorna el resultado."""
    try:
        sql = _get_sql()
        if tool_name == "query_sql":
            return sql.query_sql(args["sql"], args.get("limit", 100))

        elif tool_name == "list_tables":
            return sql.list_tables()

        elif tool_name == "describe_table":
            return sql.describe_table(args["table_name"])

        elif tool_name == "search_tables":
            return sql.search_tables(args["keyword"])

        elif tool_name == "get_row_count":
            return sql.get_row_count(args["table_name"])

        else:
            return {"error": f"Tool desconocido: {tool_name}"}

    except Exception as e:
        return {"error": str(e), "tool": tool_name, "args": args}
