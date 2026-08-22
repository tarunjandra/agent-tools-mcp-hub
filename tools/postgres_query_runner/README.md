# PostgreSQL Read-Only Query Tool

Execute read-only SQL queries against a PostgreSQL database using `psycopg2`, with parameterized execution and structured tabular results.

## Features

- **Read-Only Enforcement**: Rejects write/DDL statements (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, etc.) at the query-text level, and additionally opens the database session itself in read-only mode via `psycopg2`'s `set_session(readonly=True)`.
- **Parameterized Queries**: Prevents SQL injection by passing a list of positional parameters instead of interpolating values into the query string.
- **Structured JSON Output**: Returns a list of key-value row mappings alongside column names and execution time telemetry.
- **Configurable Limits**: Caps returned rows via `max_rows` (default `100`) and enforces a server-side `statement_timeout_ms` (default `5000`) to protect against runaway queries.
- **Flexible Connection Config**: Accepts an explicit `connection_string`, or falls back to `POSTGRES_DSN` / `DATABASE_URL` / `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` environment variables — never hardcode credentials.

## Setup

```bash
pip install -r requirements.txt
```

Configure database access via environment variables (recommended):

```bash
export POSTGRES_DSN="postgresql://user:password@host:5432/dbname"
# or individually:
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_DB="mydb"
export POSTGRES_USER="myuser"
export POSTGRES_PASSWORD="mypassword"
```

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `query` | `string` | **Yes** | — | SQL query string. Must start with `SELECT`, `WITH`, `EXPLAIN`, `SHOW`, or `TABLE` |
| `params` | `array` | No | `[]` | Positional parameter values for parameterized SQL execution |
| `connection_string` | `string` | No | env vars | PostgreSQL DSN, e.g. `postgresql://user:pass@host:5432/dbname` |
| `max_rows` | `integer` | No | `100` | Maximum number of rows to retrieve |
| `statement_timeout_ms` | `integer` | No | `5000` | Server-side statement timeout in milliseconds |

## Example Usage

### 1. Simple Query with Parameter Binding
```json
{
  "query": "SELECT id, username, email FROM users WHERE status = %s LIMIT 10",
  "params": ["active"]
}
```

### 2. Schema Introspection
```json
{
  "query": "SHOW server_version"
}
```

### Response Format
```json
{
  "status": "success",
  "columns": ["id", "username", "email"],
  "rows": [
    { "id": 1, "username": "alice", "email": "alice@example.com" },
    { "id": 2, "username": "bob", "email": "bob@example.com" }
  ],
  "row_count": 2,
  "has_more": false,
  "execution_time_ms": 4.87
}
```

### Rejected Write Statement
```json
{
  "status": "error",
  "error": "Only read-only statements (SELECT, WITH, EXPLAIN, SHOW, TABLE) are permitted.",
  "columns": [],
  "rows": [],
  "row_count": 0,
  "execution_time_ms": 0.0
}
```
