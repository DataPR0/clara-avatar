"""
SQL Tools para Clara
Consultas a SQL Server DW_FZ — 192.168.50.38\DW_FZ
Usuario: Datapros
"""

import os
import pyodbc
from dotenv import load_dotenv
from typing import Any

load_dotenv()

SQL_SERVER = os.getenv("SQL_SERVER", "192.168.50.38")
SQL_INSTANCE = os.getenv("SQL_INSTANCE", "DW_FZ")
SQL_USER = os.getenv("SQL_USER", "Datapros")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "W169n3W7FzYn")
SQL_DATABASE = os.getenv("SQL_DATABASE", "")  # vacío = usa el default del usuario


def get_connection_string() -> str:
    server = f"{SQL_SERVER}\\{SQL_INSTANCE}" if SQL_INSTANCE else SQL_SERVER
    conn = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={server};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASSWORD};"
        f"TrustServerCertificate=yes;"
        f"Encrypt=no;"
    )
    if SQL_DATABASE:
        conn += f"DATABASE={SQL_DATABASE};"
    return conn


class SqlTools:
    def __init__(self):
        self._conn_str = get_connection_string()

    def _get_conn(self):
        return pyodbc.connect(self._conn_str, timeout=15)

    def query_sql(self, sql: str, limit: int = 100) -> list[dict]:
        """
        Ejecuta una consulta SELECT en DW_FZ.
        Solo permite SELECT para seguridad.
        """
        sql_clean = sql.strip()
        if not sql_clean.upper().startswith("SELECT"):
            raise ValueError("Solo se permiten consultas SELECT")

        # Agregar TOP si no tiene LIMIT/TOP
        if "TOP " not in sql_clean.upper() and "LIMIT " not in sql_clean.upper():
            # Insertar TOP después del SELECT
            sql_clean = sql_clean.replace("SELECT ", f"SELECT TOP {limit} ", 1)

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql_clean)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    def list_tables(self) -> list[dict]:
        """Lista todas las tablas de la base de datos."""
        sql = """
        SELECT 
            TABLE_CATALOG as database_name,
            TABLE_SCHEMA as schema_name,
            TABLE_NAME as table_name,
            TABLE_TYPE as table_type
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE IN ('BASE TABLE', 'VIEW')
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    def describe_table(self, table_name: str) -> list[dict]:
        """Describe las columnas de una tabla."""
        # Soporta schema.tabla o solo tabla
        parts = table_name.split(".")
        if len(parts) == 2:
            schema, table = parts
        else:
            schema = "%"
            table = parts[0]

        sql = f"""
        SELECT 
            COLUMN_NAME as column_name,
            DATA_TYPE as data_type,
            CHARACTER_MAXIMUM_LENGTH as max_length,
            IS_NULLABLE as is_nullable,
            COLUMN_DEFAULT as default_value
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{table}'
        {'AND TABLE_SCHEMA = ' + chr(39) + schema + chr(39) if schema != '%' else ''}
        ORDER BY ORDINAL_POSITION
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    def search_tables(self, keyword: str) -> list[dict]:
        """Busca tablas cuyo nombre contiene la palabra clave."""
        sql = f"""
        SELECT 
            TABLE_SCHEMA as schema_name,
            TABLE_NAME as table_name,
            TABLE_TYPE as table_type
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME LIKE '%{keyword}%'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    def get_row_count(self, table_name: str) -> dict:
        """Retorna el número de filas de una tabla."""
        sql = f"SELECT COUNT(*) as row_count FROM {table_name}"
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            row = cursor.fetchone()
            return {"table": table_name, "row_count": row[0]}
