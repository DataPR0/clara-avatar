# Contexto SQL Server — DW_FZ

## Conexión
- **Servidor:** `192.168.50.38\DW_FZ`
- **Usuario:** `Datapros`
- **Driver:** ODBC Driver 18 for SQL Server

## Exploración inicial

Para explorar la base de datos, usa los tools disponibles:

```
1. list_tables()               → Ver todas las tablas disponibles
2. search_tables("credito")    → Buscar tablas por keyword
3. describe_table("dbo.X")     → Ver columnas de una tabla
4. query_sql("SELECT TOP 5 * FROM dbo.X")  → Ver datos de muestra
```

## Notas de seguridad
- Solo se permiten consultas **SELECT**
- Automáticamente se agrega `TOP 100` si no se especifica límite
- Nunca INSERT, UPDATE, DELETE, DROP

## Tablas descubiertas

_(Este archivo se irá completando conforme Clara explore la BD)_

| Tabla | Descripción | Columnas clave |
|-------|-------------|----------------|
| _(pendiente exploración)_ | | |
