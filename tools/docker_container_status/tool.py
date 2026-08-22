"""
Docker Container Status Checker

Queries the local Docker daemon and reports container status, health and live
resource statistics (CPU, memory, network, block I/O, PIDs).

Read-only by design: this tool never starts, stops, restarts or removes a
container. It only inspects the daemon's existing state.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Docker reports cumulative CPU counters rather than a percentage, so usage has
# to be derived from the delta between the current and previous sample. See
# _calc_cpu_percent below.
_MAX_LIMIT = 200


def _parse_docker_time(value: Optional[str]) -> Optional[datetime]:
    """
    Parses a Docker timestamp into a timezone-aware datetime.

    Docker emits RFC3339 with *nanosecond* precision (nine fractional digits),
    which datetime.fromisoformat cannot handle - it accepts at most six. The
    fractional part is therefore truncated to microseconds before parsing.
    """
    if not value or value.startswith("0001-01-01"):
        return None

    text = value.strip().replace("Z", "+00:00")
    if "." in text:
        head, _, tail = text.partition(".")
        digits = ""
        for char in tail:
            if char.isdigit():
                digits += char
            else:
                tail = tail[len(digits):]
                break
        else:
            tail = ""
        text = f"{head}.{digits[:6]}{tail}"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _calc_cpu_percent(stats: Dict[str, Any]) -> Optional[float]:
    """
    Derives CPU usage percentage from a Docker stats sample.

    The API returns cumulative nanosecond counters, not a percentage. Usage is
    the container's CPU delta over the host's total delta, scaled by the number
    of CPUs - reporting the raw counter as a percentage is a common error.
    """
    try:
        cpu = stats.get("cpu_stats") or {}
        pre = stats.get("precpu_stats") or {}

        cpu_total = (cpu.get("cpu_usage") or {}).get("total_usage")
        pre_total = (pre.get("cpu_usage") or {}).get("total_usage")
        system_total = cpu.get("system_cpu_usage")
        pre_system = pre.get("system_cpu_usage")

        if None in (cpu_total, pre_total, system_total, pre_system):
            return None

        cpu_delta = float(cpu_total) - float(pre_total)
        system_delta = float(system_total) - float(pre_system)
        if system_delta <= 0 or cpu_delta < 0:
            return 0.0

        # online_cpus is absent on older daemons; fall back to the per-CPU list.
        online = cpu.get("online_cpus")
        if not online:
            percpu = (cpu.get("cpu_usage") or {}).get("percpu_usage") or []
            online = len(percpu) or 1

        return round((cpu_delta / system_delta) * float(online) * 100.0, 2)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _calc_memory(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Derives memory usage from a Docker stats sample.

    Raw `usage` includes the page cache, which inflates the figure. Docker's own
    CLI subtracts the cache (`inactive_file` under cgroup v2, `cache` under
    cgroup v1) to report what the container is actually holding.
    """
    result: Dict[str, Any] = {
        "usage_mb": None,
        "limit_mb": None,
        "percent": None,
    }

    try:
        mem = stats.get("memory_stats") or {}
        usage = mem.get("usage")
        limit = mem.get("limit")
        if usage is None:
            return result

        detail = mem.get("stats") or {}
        cache = detail.get("inactive_file")
        if cache is None:
            cache = detail.get("cache", 0)
        real_usage = max(float(usage) - float(cache or 0), 0.0)

        result["usage_mb"] = round(real_usage / (1024 * 1024), 2)
        if limit:
            result["limit_mb"] = round(float(limit) / (1024 * 1024), 2)
            result["percent"] = round((real_usage / float(limit)) * 100.0, 2)
    except (TypeError, ValueError, ZeroDivisionError):
        return result

    return result


def _calc_io(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Totals network and block I/O across interfaces and devices."""
    rx = tx = read = write = 0
    try:
        for iface in (stats.get("networks") or {}).values():
            rx += int(iface.get("rx_bytes", 0) or 0)
            tx += int(iface.get("tx_bytes", 0) or 0)
    except (TypeError, ValueError, AttributeError):
        pass

    try:
        entries = (stats.get("blkio_stats") or {}).get("io_service_bytes_recursive") or []
        for entry in entries:
            op = str(entry.get("op", "")).lower()
            value = int(entry.get("value", 0) or 0)
            if op == "read":
                read += value
            elif op == "write":
                write += value
    except (TypeError, ValueError, AttributeError):
        pass

    return {
        "network_rx_mb": round(rx / (1024 * 1024), 3),
        "network_tx_mb": round(tx / (1024 * 1024), 3),
        "block_read_mb": round(read / (1024 * 1024), 3),
        "block_write_mb": round(write / (1024 * 1024), 3),
    }


def _ports(container: Any) -> List[str]:
    """Flattens Docker's nested port map into readable host->container strings."""
    mapped: List[str] = []
    try:
        raw = ((container.attrs or {}).get("NetworkSettings") or {}).get("Ports") or {}
        for internal, bindings in raw.items():
            if not bindings:
                mapped.append(f"{internal} (not published)")
                continue
            for binding in bindings:
                host_ip = binding.get("HostIp") or "0.0.0.0"
                host_port = binding.get("HostPort") or "?"
                # Docker's CLI brackets IPv6 hosts; without this "::" renders as ":::8080".
                display_ip = f"[{host_ip}]" if ":" in host_ip else host_ip
                mapped.append(f"{display_ip}:{host_port}->{internal}")
    except (AttributeError, TypeError):
        return mapped
    return mapped


def _summarize(container: Any, include_stats: bool) -> Dict[str, Any]:
    """Builds the reported record for a single container."""
    attrs = container.attrs or {}
    state = attrs.get("State") or {}

    started = _parse_docker_time(state.get("StartedAt"))
    uptime = None
    if started and state.get("Running"):
        uptime = int((datetime.now(timezone.utc) - started).total_seconds())

    image = ""
    try:
        tags = container.image.tags if container.image else []
        image = tags[0] if tags else (attrs.get("Config") or {}).get("Image", "")
    except Exception:
        image = (attrs.get("Config") or {}).get("Image", "")

    record: Dict[str, Any] = {
        "id": container.short_id,
        "name": container.name,
        "image": image,
        # `status` and `health` are different signals: a container can be
        # running while its healthcheck reports unhealthy.
        "status": container.status,
        "health": (state.get("Health") or {}).get("Status", "none"),
        "exit_code": state.get("ExitCode") if not state.get("Running") else None,
        "restart_count": attrs.get("RestartCount", 0),
        "started_at": started.isoformat() if started else None,
        "uptime_seconds": uptime,
        "ports": _ports(container),
    }

    if include_stats and container.status == "running":
        try:
            sample = container.stats(stream=False)
            record["stats"] = {
                "cpu_percent": _calc_cpu_percent(sample),
                "memory": _calc_memory(sample),
                "io": _calc_io(sample),
                "pids": ((sample.get("pids_stats") or {}).get("current")),
            }
        except Exception as exc:
            record["stats"] = {"error": f"Could not read stats: {exc}"}

    return record


def run_tool(
    container: str = "",
    all_containers: bool = False,
    include_stats: bool = True,
    limit: int = 25,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Reports status and live resource statistics for local Docker containers.

    Args:
        container (str): Name or ID of a single container to inspect. When
            omitted, all containers are reported.
        all_containers (bool): Include stopped containers as well as running
            ones. Ignored when `container` is given.
        include_stats (bool): Collect CPU, memory, network and I/O statistics
            for running containers. Each sample costs a daemon round trip.
        limit (int): Maximum number of containers to report (1-200).

    Returns:
        Dict[str, Any]: {"success": True, "data": {...}} on success, or
        {"success": False, "error": "..."} with a readable explanation.
    """
    try:
        import docker
        from docker.errors import APIError, DockerException, NotFound
    except ImportError:
        return {
            "success": False,
            "error": "The 'docker' package is not installed. Install it with: pip install docker",
        }

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        return {"success": False, "error": "Parameter 'limit' must be an integer."}
    limit = max(1, min(limit, _MAX_LIMIT))

    # --- Connect to the daemon ---------------------------------------------
    try:
        client = docker.from_env()
        client.ping()
    except DockerException as exc:
        # Both a stopped daemon and a permissions problem surface as the same
        # socket error, but they need different fixes, so they are separated
        # here. The raw socket repr is deliberately not passed through - it is
        # noise to a calling model and identical in both cases.
        detail = str(exc).lower()
        if "permission denied" in detail:
            message = (
                "Permission denied connecting to the Docker socket. Add your user to the 'docker' group "
                "(`sudo usermod -aG docker $USER`, then log out and back in), or run with elevated privileges."
            )
        else:
            message = (
                "Could not reach the Docker daemon - it appears to be stopped or not installed. "
                "On macOS or Windows, start Docker Desktop; on Linux, run `sudo systemctl start docker`."
            )
        return {"success": False, "error": message}
    except Exception as exc:
        return {"success": False, "error": f"Unexpected error connecting to Docker: {exc}"}

    # --- Single container --------------------------------------------------
    if container and str(container).strip():
        target = str(container).strip()
        try:
            found = client.containers.get(target)
        except NotFound:
            try:
                names = [c.name for c in client.containers.list(all=True)][:20]
            except Exception:
                names = []
            hint = f" Known containers: {', '.join(names)}." if names else " No containers exist on this host."
            return {"success": False, "error": f"No container named or matching '{target}'.{hint}"}
        except APIError as exc:
            return {"success": False, "error": f"Docker API error while fetching '{target}': {exc}"}

        return {
            "success": True,
            "data": {
                "query": target,
                "container_count": 1,
                "containers": [_summarize(found, include_stats)],
            },
        }

    # --- All containers ----------------------------------------------------
    try:
        found = client.containers.list(all=bool(all_containers))
    except APIError as exc:
        return {"success": False, "error": f"Docker API error while listing containers: {exc}"}

    if not found:
        scope = "any state" if all_containers else "a running state"
        return {
            "success": True,
            "data": {
                "query": "all" if all_containers else "running",
                "container_count": 0,
                "containers": [],
                "note": f"The Docker daemon is reachable but no containers are in {scope}.",
            },
        }

    selected = found[:limit]
    try:
        version = (client.version() or {}).get("Version", "")
    except Exception:
        version = ""

    return {
        "success": True,
        "data": {
            "query": "all" if all_containers else "running",
            "docker_version": version,
            "container_count": len(selected),
            "total_found": len(found),
            "containers": [_summarize(c, include_stats) for c in selected],
        },
    }


if __name__ == "__main__":
    output = run_tool()
    print("Test execution output:", output)
