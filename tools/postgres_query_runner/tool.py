#!/usr/bin/env python3
"""
PostgreSQL Read-Only Query Tool for Agent Tools & MCP Hub.
Executes parameterized, read-only SQL queries against a PostgreSQL database using psycopg2.
"""
from typing import Any, Dict, List, Optional
import os
import time

import psycopg2
import psycopg2.extras


DISALLOWED_READONLY_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "REPLACE", "GRANT", "REVOKE", "VACUUM", "COPY", "CALL"
}

ALLOWED_STATEMENT_STARTS = {"SELECT", "WITH", "EXPLAIN", "SHOW", "TABLE"}


def is_safe_readonly_query(sql: str) -> bool:
    """Validate whether an SQL string is purely read-only."""
    cleaned = sql.strip().rstrip(";").upper()
    tokens = cleaned.split()
    if not tokens:
        return False
    if tokens[0] not in ALLOWED_STATEMENT_STARTS:
        return False
    for kw in DISALLOWED_READONLY_KEYWORDS:
        if f" {kw} " in f" {cleaned} ":
            return False
    return True


def _resolve_dsn(connection_string: Optional[str]) -> str:
    """Resolve a PostgreSQL DSN from the explicit param or environment variables."""
    if connection_string:
        return connection_string

    dsn = os.environ.get("POSTGRES_DSN") or os.environ.get("DATABASE_URL")
    if dsn:
        return dsn

    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    dbname = os.environ.get("POSTGRES_DB", "")
    user = os.environ.get("POSTGRES_USER", "")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


def execute_postgres_query(
    query: str,
    params: Optional[List[Any]] = None,
    connection_string: Optional[str] = None,
    max_rows: int = 100,
    statement_timeout_ms: int = 5000
) -> Dict[str, Any]:
    """
    Execute a read-only query against a PostgreSQL database.

    Args:
        query: SQL string to execute. Must be a read-only statement.
        params: Optional parameter list for parameterized queries.
        connection_string: Optional PostgreSQL DSN; falls back to env vars.
        max_rows: Maximum number of rows to return.
        statement_timeout_ms: Server-side statement timeout in milliseconds.

    Returns:
        Dictionary containing columns, rows, row_count, execution_time_ms, and status.
    """
    start_time = time.perf_counter()

    if not is_safe_readonly_query(query):
        return {
            "status": "error",
            "error": "Only read-only statements (SELECT, WITH, EXPLAIN, SHOW, TABLE) are permitted.",
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": 0.0
        }

    dsn = _resolve_dsn(connection_string)
    conn = None
    try:
        conn = psycopg2.connect(dsn, connect_timeout=10)
        # Enforce read-only at the session/transaction level as a second safeguard
        # beyond the textual keyword check above.
        conn.set_session(readonly=True, autocommit=True)

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SET statement_timeout = %s", (int(statement_timeout_ms),))
            query_params = tuple(params) if params is not None else None
            cursor.execute(query, query_params)

            if cursor.description:
                columns = [col[0] for col in cursor.description]
                raw_rows = cursor.fetchmany(max_rows)
                rows = [dict(row) for row in raw_rows]
                row_count = len(rows)
            else:
                columns = []
                rows = []
                row_count = 0

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)

        return {
            "status": "success",
            "columns": columns,
            "rows": rows,
            "row_count": row_count,
            "has_more": row_count == max_rows,
            "execution_time_ms": elapsed_ms
        }

    except psycopg2.Error as e:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
        return {
            "status": "error",
            "error": f"PostgreSQL error: {str(e).strip()}",
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": elapsed_ms
        }
    finally:
        if conn:
            conn.close()


def run(params: Dict[str, Any]) -> Dict[str, Any]:
    """Standard entry point for MCP agent tools."""
    query = params.get("query", "")
    query_params = params.get("params")
    connection_string = params.get("connection_string")
    max_rows = params.get("max_rows", 100)
    statement_timeout_ms = params.get("statement_timeout_ms", 5000)

    return execute_postgres_query(
        query=query,
        params=query_params,
        connection_string=connection_string,
        max_rows=max_rows,
        statement_timeout_ms=statement_timeout_ms
    )


if __name__ == "__main__":
    # Self-test requires a reachable PostgreSQL instance, configured via
    # POSTGRES_DSN / DATABASE_URL or POSTGRES_HOST/PORT/DB/USER/PASSWORD.
    if not (os.environ.get("POSTGRES_DSN") or os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_HOST")):
        print("Skipping live self-test: no PostgreSQL connection configured.")
    else:
        res = run({"query": "SELECT 1 AS ok"})
        print("Test Result:", res)
        assert res["status"] == "success"
        assert res["rows"][0]["ok"] == 1
        print("Self-test passed successfully!")

    # Query-safety checks that don't require a live database.
    assert is_safe_readonly_query("SELECT * FROM users") is True
    assert is_safe_readonly_query("WITH t AS (SELECT 1) SELECT * FROM t") is True
    assert is_safe_readonly_query("DELETE FROM users") is False
    assert is_safe_readonly_query("SELECT * FROM users; DROP TABLE users;") is False
    print("Read-only validation checks passed!")
