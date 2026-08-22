#!/usr/bin/env python3
"""
SQLite Query Runner Tool for Agent Tools & MCP Hub.
Executes parameterized queries safely with read-only safeguards and structured row output.
"""
from typing import Any, Dict, List, Optional, Sequence, Tuple
import os
import re
import sqlite3
import time
from pathlib import Path


DISALLOWED_READONLY_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
    "TRUNCATE", "REPLACE", "VACUUM", "ATTACH", "DETACH",
    "GRANT", "REVOKE", "REINDEX", "ANALYZE",
}

ALLOWED_READONLY_STARTERS = {"SELECT", "PRAGMA", "EXPLAIN", "WITH"}

# Strip /* ... */ and -- line comments before keyword checks.
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"--.*?$", re.MULTILINE)
_STRING_LITERAL_RE = re.compile(
    r"('(?:''|[^'])*')|(\"(?:\"\"|[^\"])*\")"
)
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _strip_sql_comments(sql: str) -> str:
    """Remove SQL comments while preserving string literal contents."""
    placeholders: List[str] = []

    def _stash(match: re.Match) -> str:
        placeholders.append(match.group(0))
        return f"__SQL_STR_{len(placeholders) - 1}__"

    masked = _STRING_LITERAL_RE.sub(_stash, sql)
    masked = _BLOCK_COMMENT_RE.sub(" ", masked)
    masked = _LINE_COMMENT_RE.sub(" ", masked)

    def _restore(match: re.Match) -> str:
        return placeholders[int(match.group(1))]

    return re.sub(r"__SQL_STR_(\d+)__", _restore, masked)


def _split_statements(sql: str) -> List[str]:
    """Split on semicolons outside of string literals."""
    statements: List[str] = []
    buf: List[str] = []
    in_single = False
    in_double = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'" and not in_double:
            if in_single and i + 1 < len(sql) and sql[i + 1] == "'":
                buf.append("''")
                i += 2
                continue
            in_single = not in_single
            buf.append(ch)
        elif ch == '"' and not in_single:
            if in_double and i + 1 < len(sql) and sql[i + 1] == '"':
                buf.append('""')
                i += 2
                continue
            in_double = not in_double
            buf.append(ch)
        elif ch == ";" and not in_single and not in_double:
            part = "".join(buf).strip()
            if part:
                statements.append(part)
            buf = []
        else:
            buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def _keywords_outside_strings(sql: str) -> List[str]:
    """Return uppercase SQL keywords found outside string literals."""
    keywords: List[str] = []
    for match in _WORD_RE.finditer(sql):
        start = match.start()
        # Cheap check: if an odd number of unescaped quotes precede, skip.
        before = sql[:start]
        # Count single quotes not doubled
        singles = 0
        j = 0
        while j < len(before):
            if before[j] == "'":
                if j + 1 < len(before) and before[j + 1] == "'":
                    j += 2
                    continue
                singles += 1
            j += 1
        if singles % 2 == 1:
            continue
        doubles = 0
        j = 0
        while j < len(before):
            if before[j] == '"':
                if j + 1 < len(before) and before[j + 1] == '"':
                    j += 2
                    continue
                doubles += 1
            j += 1
        if doubles % 2 == 1:
            continue
        keywords.append(match.group(0).upper())
    return keywords


def is_safe_readonly_query(sql: str) -> bool:
    """
    Validate whether an SQL string is a single read-only statement.

    Allows SELECT (including UNION SELECT), PRAGMA, EXPLAIN, and WITH
    (read-only CTEs). Rejects multi-statement scripts and write/DDL keywords.
    """
    if not sql or not sql.strip():
        return False

    cleaned = _strip_sql_comments(sql).strip()
    statements = _split_statements(cleaned)
    if len(statements) != 1:
        return False

    statement = statements[0]
    tokens = _keywords_outside_strings(statement)
    if not tokens:
        return False

    # EXPLAIN [QUERY PLAN] SELECT ...
    idx = 0
    if tokens[0] == "EXPLAIN":
        idx = 1
        if idx < len(tokens) and tokens[idx] == "QUERY":
            idx += 1
            if idx < len(tokens) and tokens[idx] == "PLAN":
                idx += 1
        if idx >= len(tokens):
            return False

    starter = tokens[idx]
    if starter not in ALLOWED_READONLY_STARTERS:
        return False

    # Reject any write/DDL keyword appearing as a real SQL token.
    for token in tokens:
        if token in DISALLOWED_READONLY_KEYWORDS:
            return False

    return True


def _parse_allowed_roots(
    allowed_roots: Optional[Sequence[str]] = None,
) -> List[Path]:
    """
    Resolve allowlisted directories for database_path containment.

    Priority:
      1. Explicit `allowed_roots` argument
      2. SQLITE_ALLOWED_ROOTS env (os.pathsep-separated)
      3. Current working directory (safe default)
    """
    if allowed_roots is None:
        env_value = os.environ.get("SQLITE_ALLOWED_ROOTS", "").strip()
        if env_value:
            allowed_roots = [p for p in env_value.split(os.pathsep) if p.strip()]
        else:
            allowed_roots = [os.getcwd()]

    roots: List[Path] = []
    for raw in allowed_roots:
        try:
            roots.append(Path(raw).expanduser().resolve(strict=False))
        except OSError:
            continue
    return roots


def is_path_within_allowed_roots(
    database_path: str,
    allowed_roots: Optional[Sequence[str]] = None,
) -> Tuple[bool, str, Optional[Path]]:
    """
    Ensure database_path resolves inside an allowlisted directory tree.
    Returns (ok, error_message, resolved_path).
    """
    roots = _parse_allowed_roots(allowed_roots)
    if not roots:
        return False, "No allowed database directories configured.", None

    try:
        resolved = Path(database_path).expanduser().resolve(strict=False)
    except OSError as exc:
        return False, f"Invalid database_path: {exc}", None

    for root in roots:
        try:
            resolved.relative_to(root)
            return True, "", resolved
        except ValueError:
            continue

    roots_display = ", ".join(str(r) for r in roots)
    return (
        False,
        (
            f"database_path '{database_path}' is outside allowed directories "
            f"[{roots_display}]. Set SQLITE_ALLOWED_ROOTS or pass "
            f"allowed_roots to permit additional locations."
        ),
        None,
    )


def execute_sqlite_query(
    database_path: str,
    query: str,
    params: Optional[List[Any]] = None,
    read_only: bool = True,
    max_rows: int = 100,
    allowed_roots: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """
    Execute a query against a local SQLite database file.

    Args:
        database_path: Path to the SQLite file.
        query: SQL string to execute.
        params: Optional parameter list for parameterized queries.
        read_only: If True, blocks write/destructive SQL statements.
        max_rows: Maximum number of rows to return.
        allowed_roots: Optional directory allowlist for path containment.
            Defaults to SQLITE_ALLOWED_ROOTS or the process cwd.

    Returns:
        Dictionary containing columns, rows, row_count, execution_time_ms, and status.
    """
    start_time = time.perf_counter()

    path_ok, path_error, resolved_path = is_path_within_allowed_roots(
        database_path, allowed_roots=allowed_roots
    )
    if not path_ok or resolved_path is None:
        return {
            "status": "error",
            "error": path_error,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": 0.0,
        }

    normalized_path = str(resolved_path)

    if not resolved_path.exists() and read_only:
        return {
            "status": "error",
            "error": f"Database file not found: {database_path}",
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": 0.0,
        }

    if read_only and not is_safe_readonly_query(query):
        return {
            "status": "error",
            "error": (
                "Only a single read-only statement is allowed when "
                "read_only=True (SELECT/PRAGMA/EXPLAIN/WITH). "
                "Write, DDL, ATTACH, and multi-statement queries are prohibited."
            ),
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": 0.0,
        }

    conn = None
    try:
        if read_only:
            # Connect in URI read-only mode if file exists
            # Use forward slashes for SQLite URI on all platforms.
            uri_file = resolved_path.as_posix()
            uri_path = f"file:{uri_file}?mode=ro"
            conn = sqlite3.connect(uri_path, uri=True, timeout=10.0)
        else:
            conn = sqlite3.connect(normalized_path, timeout=10.0)

        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query_params = tuple(params) if params is not None else ()
        cursor.execute(query, query_params)

        if cursor.description:
            columns = [col[0] for col in cursor.description]
            raw_rows = cursor.fetchmany(max_rows)
            rows = [dict(row) for row in raw_rows]
            row_count = len(rows)
        else:
            columns = []
            rows = []
            row_count = cursor.rowcount if cursor.rowcount != -1 else 0
            if not read_only:
                conn.commit()

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)

        return {
            "status": "success",
            "database": resolved_path.name,
            "columns": columns,
            "rows": rows,
            "row_count": row_count,
            "has_more": len(rows) == max_rows,
            "execution_time_ms": elapsed_ms,
        }

    except sqlite3.Error as e:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
        return {
            "status": "error",
            "error": f"SQLite error: {str(e)}",
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": elapsed_ms,
        }
    finally:
        if conn:
            conn.close()


def run(params: Dict[str, Any]) -> Dict[str, Any]:
    """Standard entry point for MCP agent tools."""
    db_path = params.get("database_path", "")
    query = params.get("query", "")
    sql_params = params.get("params")
    read_only = params.get("read_only", True)
    max_rows = params.get("max_rows", 100)
    allowed_roots = params.get("allowed_roots")

    return execute_sqlite_query(
        database_path=db_path,
        query=query,
        params=sql_params,
        read_only=read_only,
        max_rows=max_rows,
        allowed_roots=allowed_roots,
    )


if __name__ == "__main__":
    # Self-test using a temporary sqlite db under an allowlisted directory.
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_db = os.path.join(tmp_dir, "test.db")
        init_conn = sqlite3.connect(tmp_db)
        init_conn.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, role TEXT);"
        )
        init_conn.execute(
            "CREATE TABLE secrets (id INTEGER PRIMARY KEY, value TEXT);"
        )
        init_conn.execute(
            "INSERT INTO users (name, role) VALUES ('Alice', 'Admin'), ('Bob', 'Developer');"
        )
        init_conn.execute(
            "INSERT INTO secrets (value) VALUES ('FLAG-top-secret-42');"
        )
        init_conn.commit()
        init_conn.close()

        # Legitimate parameterized SELECT
        res = run(
            {
                "database_path": tmp_db,
                "query": "SELECT * FROM users WHERE role = ?",
                "params": ["Developer"],
                "allowed_roots": [tmp_dir],
            }
        )
        print("Test Result:", res)
        assert res["status"] == "success"
        assert res["row_count"] == 1
        assert res["rows"][0]["name"] == "Bob"

        # Multi-statement write attempt must be rejected
        blocked = run(
            {
                "database_path": tmp_db,
                "query": "SELECT 1; DELETE FROM users",
                "allowed_roots": [tmp_dir],
            }
        )
        assert blocked["status"] == "error", blocked

        # Comment-smuggled write must be rejected
        comment_bypass = run(
            {
                "database_path": tmp_db,
                "query": "SELECT 1 /* INSERT */; DELETE FROM users",
                "allowed_roots": [tmp_dir],
            }
        )
        assert comment_bypass["status"] == "error", comment_bypass

        # Path outside allowlist must be rejected
        outside = run(
            {
                "database_path": tmp_db,
                "query": "SELECT 1",
                "allowed_roots": [os.path.join(tmp_dir, "does-not-exist-root")],
            }
        )
        assert outside["status"] == "error", outside
        assert "outside allowed directories" in outside["error"]

        # UNION SELECT remains a valid read-only query (same DB, allowlisted path)
        union_ok = run(
            {
                "database_path": tmp_db,
                "query": "SELECT name FROM users UNION SELECT value FROM secrets",
                "allowed_roots": [tmp_dir],
            }
        )
        assert union_ok["status"] == "success", union_ok

        print("Self-test passed successfully!")
