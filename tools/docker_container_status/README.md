# Docker Container Status Checker

Query the local Docker daemon for container status, health and live resource statistics.

**Read-only** — this tool never starts, stops, restarts or removes a container. It only inspects existing state.

## Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `container` | `string` | No | Name or ID of a single container to inspect. Omit to report all containers. |
| `all_containers` | `boolean` | No | Include stopped containers as well as running ones (default `false`) |
| `include_stats` | `boolean` | No | Collect CPU, memory, network and I/O statistics (default `true`) |
| `limit` | `integer` | No | Maximum containers to report, 1–200 (default `25`) |

## Installation & Setup

```bash
pip install -r requirements.txt
```

Requires a running Docker daemon. On macOS and Windows start Docker Desktop; on Linux run `sudo systemctl start docker`.

## Usage Example

```python
from tool import run_tool

# All running containers, with live stats
result = run_tool()

# One container by name
result = run_tool(container="my-api")

# Everything including stopped containers, no stats collection
result = run_tool(all_containers=True, include_stats=False)
```

### Example output

```json
{
  "success": true,
  "data": {
    "query": "running",
    "docker_version": "27.1.1",
    "container_count": 1,
    "total_found": 1,
    "containers": [
      {
        "id": "a1b2c3d4e5f6",
        "name": "test-nginx",
        "image": "nginx:latest",
        "status": "running",
        "health": "healthy",
        "exit_code": null,
        "restart_count": 2,
        "started_at": "2026-08-22T09:00:00.123456+00:00",
        "uptime_seconds": 21600,
        "ports": ["0.0.0.0:8080->80/tcp"],
        "stats": {
          "cpu_percent": 12.4,
          "memory": { "usage_mb": 80.0, "limit_mb": 512.0, "percent": 15.62 },
          "io": {
            "network_rx_mb": 1.0,
            "network_tx_mb": 0.5,
            "block_read_mb": 2.0,
            "block_write_mb": 0.0
          },
          "pids": 7
        }
      }
    ]
  }
}
```

### Error output

Errors are returned as data rather than raised, so a calling agent can read and act on them:

```json
{
  "success": false,
  "error": "Could not reach the Docker daemon - it appears to be stopped or not installed. On macOS or Windows, start Docker Desktop; on Linux, run `sudo systemctl start docker`."
}
```

## Notes

- **`status` and `health` are separate signals.** A container can report `running` while its healthcheck reports `unhealthy`. An agent asking whether a service is actually up needs both, so both are returned; `health` is `"none"` when no healthcheck is configured.
- **CPU percentage is computed, not read.** Docker returns cumulative nanosecond counters, not a percentage. Usage is derived as the container's CPU delta over the host's total delta, scaled by CPU count — reporting the raw counter as a percentage is a common error. The first sample after a container starts has no previous reading to compare against, so `cpu_percent` is `null` rather than a fabricated zero. Values above 100% are correct and expected on multi-core hosts.
- **Memory excludes page cache.** Raw `usage` counts the page cache, which inflates the figure. The cache is subtracted (`inactive_file` under cgroup v2, `cache` under cgroup v1) to match what `docker stats` reports.
- **Docker timestamps carry nanosecond precision** — nine fractional digits, which `datetime.fromisoformat` rejects. They are truncated to microseconds before parsing rather than failing.
- **A stopped daemon and a permissions problem produce the same socket error** but need different fixes, so they are reported separately. The raw socket exception is not passed through, as it is identical in both cases and unreadable to a calling model.
- **Each stats sample costs a daemon round trip.** Set `include_stats: false` when only status is needed across many containers.
- **A daemon with no containers returns `success: true`** with an empty list and a note — nothing running is a valid state, not a failure.
