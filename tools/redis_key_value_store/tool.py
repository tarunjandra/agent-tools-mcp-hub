"""
Redis Key-Value Store Tool

Provides simple GET and SET operations against a Redis instance.
"""

import os
from typing import Any, Dict

import redis
from redis import Redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError


def _get_redis_client() -> Redis:
    """
    Build a Redis client from environment variables.
    """

    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD")
    db = int(os.getenv("REDIS_DB", "0"))

    ssl_value = os.getenv("REDIS_SSL", "false").strip().lower()
    use_ssl = ssl_value in {"1", "true", "yes", "on"}

    return redis.Redis(
        host=host,
        port=port,
        password=password,
        db=db,
        ssl=use_ssl,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def run_tool(query: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Get or set a Redis key.

    Args:
        query:
            Redis key.

        action:
            "get" or "set".
            Defaults to "get".

        value:
            Required when action="set".

        ttl:
            Optional expiration time in seconds for SET.

    Environment Variables:
        REDIS_HOST
        REDIS_PORT
        REDIS_PASSWORD
        REDIS_DB
        REDIS_SSL

    Returns:
        Structured dictionary containing the Redis operation result.
    """

    if not query or not query.strip():
        return {
            "success": False,
            "error": "Redis key is required.",
        }

    key = query.strip()
    action = str(kwargs.get("action", "get")).strip().lower()

    if action not in {"get", "set"}:
        return {
            "success": False,
            "error": "action must be either 'get' or 'set'.",
        }

    try:
        client = _get_redis_client()

        if action == "get":
            value = client.get(key)

            return {
                "success": True,
                "action": "get",
                "key": key,
                "found": value is not None,
                "value": value,
            }

        value = kwargs.get("value")

        if value is None:
            return {
                "success": False,
                "error": "value is required when action='set'.",
            }

        ttl = kwargs.get("ttl")

        if ttl is not None:
            try:
                ttl = int(ttl)
            except (TypeError, ValueError):
                return {
                    "success": False,
                    "error": "ttl must be an integer number of seconds.",
                }

            if ttl <= 0:
                return {
                    "success": False,
                    "error": "ttl must be greater than 0.",
                }

        if ttl is not None:
            result = client.set(
                key,
                str(value),
                ex=ttl,
            )
        else:
            result = client.set(
                key,
                str(value),
            )

        return {
            "success": bool(result),
            "action": "set",
            "key": key,
            "value": str(value),
            "ttl": ttl,
        }

    except (ConnectionError, TimeoutError) as exc:
        return {
            "success": False,
            "error": f"Unable to connect to Redis: {exc}",
        }

    except RedisError as exc:
        return {
            "success": False,
            "error": f"Redis operation failed: {exc}",
        }

    except ValueError as exc:
        return {
            "success": False,
            "error": f"Invalid Redis configuration: {exc}",
        }