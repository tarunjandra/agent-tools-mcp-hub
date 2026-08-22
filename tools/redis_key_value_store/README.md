# Redis Key-Value Store

A Python Agent Tool for getting and setting cached values in Redis.

## Features

- Get values by Redis key
- Set Redis key-value pairs
- Optional TTL expiration
- Environment-based Redis configuration
- Optional Redis SSL connection
- Structured connection and Redis error handling
- MCP-compatible metadata

## Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `query` | string | Yes | Redis key |
| `action` | string | No | `get` or `set`; defaults to `get` |
| `value` | string | For `set` | Value to store |
| `ttl` | integer | No | Expiration time in seconds for a stored value |

## Environment Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `REDIS_HOST` | No | `localhost` | Redis server host |
| `REDIS_PORT` | No | `6379` | Redis server port |
| `REDIS_PASSWORD` | No | None | Redis password |
| `REDIS_DB` | No | `0` | Redis database number |
| `REDIS_SSL` | No | `false` | Enable SSL when set to `true` |

## Installation

```bash
pip install -r requirements.txt
```

## Get a Value

```python
from tool import run_tool

result = run_tool(
    query="customer:123",
    action="get"
)

print(result)
```

Example response:

```json
{
  "success": true,
  "action": "get",
  "key": "customer:123",
  "found": true,
  "value": "active"
}
```

## Set a Value

```python
from tool import run_tool

result = run_tool(
    query="customer:123",
    action="set",
    value="active"
)

print(result)
```

## Set a Value with TTL

```python
from tool import run_tool

result = run_tool(
    query="session:abc123",
    action="set",
    value="authenticated",
    ttl=3600
)

print(result)
```

Example response:

```json
{
  "success": true,
  "action": "set",
  "key": "session:abc123",
  "value": "authenticated",
  "ttl": 3600
}
```

## Configuration

PowerShell example:

```powershell
$env:REDIS_HOST="localhost"
$env:REDIS_PORT="6379"
$env:REDIS_DB="0"
$env:REDIS_SSL="false"
```

If authentication is required:

```powershell
$env:REDIS_PASSWORD="your_password"
```

## Security

Never commit Redis credentials to the repository.

Use environment variables or a secure secrets manager for production credentials.