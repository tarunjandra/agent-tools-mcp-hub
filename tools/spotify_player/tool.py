"""
Spotify Current Track and Playlist Tool for AI Agents and MCP Hub.
"""
import base64
import json
import os
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

API_BASE = "https://api.spotify.com/v1"
TOKEN_URL = "https://accounts.spotify.com/api/token"
USER_AGENT = "AgentToolsHub/1.0"
TIMEOUT = 15

ACTIONS = ("current_track", "playlists", "playlist")
SCOPES = (
    "user-read-currently-playing",
    "playlist-read-private",
    "playlist-read-collaborative",
)
DEFAULT_LIMIT = 10
MAX_LIMIT = 50
MAX_OFFSET = 100000

# Ask for podcast episodes too; without this Spotify returns item=None while an episode plays.
ADDITIONAL_TYPES = "track,episode"

_STATUS_MESSAGES = {
    400: "Bad request",
    401: "Unauthorized: invalid or expired access token",
    403: "Forbidden: missing OAuth scope, user not allowlisted for this Development Mode app, "
         "or the resource is not available to this user",
    404: "Not found",
    429: "Too Many Requests: rate limited by Spotify",
}

# Access token from the refresh flow, reused until shortly before it expires.
_token_cache: Dict[str, Any] = {
    "key": None,
    "access_token": None,
    "expires_at": 0.0,
    "refresh_token": None,
}


class SpotifyError(Exception):
    def __init__(self, message: str, status: Optional[int] = None, retry_after: Optional[int] = None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


def _int_param(value: Any, name: str, default: int, minimum: int, maximum: int) -> int:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer, not a boolean.")
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"{name} must be a whole number.")
        value = int(value)
    elif isinstance(value, str):
        try:
            value = int(value.strip())
        except ValueError:
            raise ValueError(f"{name} must be an integer.") from None
    elif not isinstance(value, int):
        raise ValueError(f"{name} must be an integer.")
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return value


def _bool_param(value: Any, name: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in ("true", "1", "yes"):
        return True
    if isinstance(value, str) and value.strip().lower() in ("false", "0", "no"):
        return False
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise ValueError(f"{name} must be true or false.")


def _parse_playlist_id(value: Any) -> str:
    """Accepts a bare ID, a spotify:playlist: URI or an open.spotify.com playlist URL."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("playlist_id is required for action 'playlist'.")
    match = re.search(r"playlist[:/]([A-Za-z0-9]+)", value)
    playlist_id = match.group(1) if match else value.strip()
    if not re.fullmatch(r"[A-Za-z0-9]+", playlist_id):
        raise ValueError(f"Invalid playlist_id '{value}'. Pass a playlist ID, URI or open.spotify.com URL.")
    return playlist_id


def _read_error_body(e: urllib.error.HTTPError) -> Dict[str, Any]:
    try:
        body = json.loads(e.read().decode("utf-8"))
        return body if isinstance(body, dict) else {}
    except Exception:
        return {}


def _can_refresh() -> bool:
    return bool(os.getenv("SPOTIFY_CLIENT_ID") and os.getenv("SPOTIFY_REFRESH_TOKEN"))


def _refresh_access_token() -> str:
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    env_refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN", "")
    key = (client_id, env_refresh_token)

    # Spotify may rotate the refresh token; keep using the newest one for these credentials.
    refresh_token = env_refresh_token
    if _token_cache["key"] == key and _token_cache["refresh_token"]:
        refresh_token = _token_cache["refresh_token"]

    form = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    headers = {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": USER_AGENT}
    if client_secret:
        basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {basic}"
    else:
        # Tokens from the PKCE flow are refreshed without a client secret.
        form["client_id"] = client_id

    req = urllib.request.Request(
        TOKEN_URL, data=urllib.parse.urlencode(form).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = _read_error_body(e)
        code = body.get("error")
        if code == "invalid_grant":
            raise SpotifyError(
                "Refresh token is invalid, expired or revoked. Run auth_helper.py to authorize again.",
                status=e.code,
            ) from None
        if code == "invalid_client":
            raise SpotifyError(
                "Spotify rejected the client credentials. Check SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.",
                status=e.code,
            ) from None
        detail = body.get("error_description") or code
        message = f"Token refresh failed: HTTP {e.code}" + (f" - {detail}" if detail else "")
        raise SpotifyError(message, status=e.code) from None

    access_token = payload.get("access_token")
    if not access_token:
        raise SpotifyError("Token refresh response did not include an access token.")
    _token_cache.update(
        key=key,
        access_token=access_token,
        expires_at=time.time() + int(payload.get("expires_in", 3600)),
        refresh_token=payload.get("refresh_token") or refresh_token,
    )
    return access_token


def _get_access_token(force_refresh: bool = False) -> str:
    if _can_refresh():
        key = (os.getenv("SPOTIFY_CLIENT_ID"), os.getenv("SPOTIFY_REFRESH_TOKEN"))
        cached = _token_cache["access_token"]
        if not force_refresh and cached and _token_cache["key"] == key and time.time() < _token_cache["expires_at"] - 60:
            return cached
        return _refresh_access_token()

    token = os.getenv("SPOTIFY_ACCESS_TOKEN")
    if not token:
        raise SpotifyError(
            "Spotify credentials are missing. Set SPOTIFY_ACCESS_TOKEN, or SPOTIFY_CLIENT_ID and "
            "SPOTIFY_REFRESH_TOKEN (plus SPOTIFY_CLIENT_SECRET unless you authorized with PKCE)."
        )
    return token


def _http_error(e: urllib.error.HTTPError) -> SpotifyError:
    message = _STATUS_MESSAGES.get(e.code, f"HTTP Error {e.code}: {e.reason}")
    detail = _read_error_body(e).get("error")
    if isinstance(detail, dict) and detail.get("message"):
        message += f" - {detail['message']}"

    retry_after = None
    if e.code == 429:
        try:
            retry_after = int((e.headers or {}).get("Retry-After"))
        except (TypeError, ValueError):
            pass
        if retry_after is not None:
            message += f". Retry after {retry_after} seconds."
    return SpotifyError(message, status=e.code, retry_after=retry_after)


def _api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    for attempt in range(2):
        token = _get_access_token(force_refresh=attempt > 0)
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        })
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                body = response.read().decode("utf-8")
                if response.status == 204 or not body.strip():  # e.g. nothing is playing
                    return None
                return json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 401 and attempt == 0 and _can_refresh():
                continue  # The cached token was revoked early; refresh once and retry.
            raise _http_error(e) from None
    return None


def _spotify_url(obj: Dict[str, Any]) -> Optional[str]:
    return (obj.get("external_urls") or {}).get("spotify")


def _summarize_item(item: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not item:
        return None
    if item.get("type") == "episode":
        return {
            "type": "episode",
            "id": item.get("id"),
            "name": item.get("name"),
            "show": (item.get("show") or {}).get("name"),
            "duration_ms": item.get("duration_ms"),
            "release_date": item.get("release_date"),
            "explicit": item.get("explicit"),
            "url": _spotify_url(item),
            "uri": item.get("uri"),
        }
    return {
        "type": item.get("type", "track"),
        "id": item.get("id"),
        "name": item.get("name"),
        "artists": [a.get("name") for a in item.get("artists") or [] if a],
        "album": (item.get("album") or {}).get("name"),
        "duration_ms": item.get("duration_ms"),
        "explicit": item.get("explicit"),
        "is_local": item.get("is_local", False),
        "url": _spotify_url(item),
        "uri": item.get("uri"),
    }


def _summarize_playback(data: Dict[str, Any]) -> Dict[str, Any]:
    context = data.get("context")
    return {
        "is_playing": data.get("is_playing"),
        "progress_ms": data.get("progress_ms"),
        "currently_playing_type": data.get("currently_playing_type"),
        "item": _summarize_item(data.get("item")),
        "context": {
            "type": context.get("type"),
            "uri": context.get("uri"),
            "url": _spotify_url(context),
        } if context else None,
    }


def _summarize_playlist(playlist: Dict[str, Any]) -> Dict[str, Any]:
    # Spotify renamed the playlist "tracks" field to "items" in February 2026.
    contents = playlist.get("items") if isinstance(playlist.get("items"), dict) else playlist.get("tracks")
    owner = playlist.get("owner") or {}
    images = playlist.get("images") or []
    return {
        "id": playlist.get("id"),
        "name": playlist.get("name"),
        "description": playlist.get("description"),
        "owner": owner.get("display_name") or owner.get("id"),
        "owner_id": owner.get("id"),
        "public": playlist.get("public"),
        "collaborative": playlist.get("collaborative"),
        "item_count": (contents or {}).get("total"),
        "image": images[0].get("url") if images and images[0] else None,
        "url": _spotify_url(playlist),
        "uri": playlist.get("uri"),
        "snapshot_id": playlist.get("snapshot_id"),
    }


def _summarize_playlist_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    # Playlist entries renamed "track" to "item" in February 2026.
    item = entry.get("item") if "item" in entry else entry.get("track")
    return {
        "added_at": entry.get("added_at"),
        "added_by": (entry.get("added_by") or {}).get("id"),
        "item": _summarize_item(item),
    }


def _page_info(page: Dict[str, Any], limit: int, offset: int) -> Dict[str, Any]:
    return {
        "total": page.get("total"),
        "limit": limit,
        "offset": offset,
        "next_offset": offset + limit if page.get("next") else None,
    }


def _current_track(raw: bool) -> Dict[str, Any]:
    data = _api_get("/me/player/currently-playing", {"additional_types": ADDITIONAL_TYPES})
    if data is None:
        return {"success": True, "data": None, "message": "No track is currently playing."}
    if raw:
        return {"success": True, "data": data}

    summary = _summarize_playback(data)
    result: Dict[str, Any] = {"success": True, "data": summary}
    if summary["item"] is None:
        result["message"] = "Spotify returned no details for the current item (an ad or unsupported content may be playing)."
    return result


def _playlists(limit: int, offset: int, raw: bool) -> Dict[str, Any]:
    page = _api_get("/me/playlists", {"limit": limit, "offset": offset}) or {}
    if raw:
        return {"success": True, "data": page}
    playlists = [_summarize_playlist(p) for p in page.get("items") or [] if p]
    return {"success": True, "data": {"playlists": playlists, **_page_info(page, limit, offset)}}


def _playlist(playlist_id: str, include_items: bool, limit: int, offset: int, raw: bool) -> Dict[str, Any]:
    try:
        metadata = _api_get(f"/playlists/{playlist_id}") or {}
    except SpotifyError as e:
        if e.status != 404:
            raise
        raise SpotifyError(
            f"{e}. Spotify-owned editorial and algorithmic playlists (e.g. Discover Weekly) "
            "are not available to Development Mode apps.",
            status=404,
        ) from None
    data: Dict[str, Any] = {"playlist": metadata if raw else _summarize_playlist(metadata)}
    result: Dict[str, Any] = {"success": True, "data": data}
    if not include_items:
        return result

    params = {"limit": limit, "offset": offset, "additional_types": ADDITIONAL_TYPES}
    try:
        page = _api_get(f"/playlists/{playlist_id}/items", params) or {}
    except SpotifyError as e:
        if e.status != 403:
            raise
        data["items"] = None
        result["message"] = (
            "Returned playlist metadata only. Spotify only exposes the contents of the "
            "authorized user's own playlists."
        )
        return result

    if raw:
        data["items"] = page
    else:
        data["items"] = [_summarize_playlist_entry(entry) for entry in page.get("items") or [] if entry]
        data.update(_page_info(page, limit, offset))
    return result


def run_tool(
    action: str,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    playlist_id: Optional[str] = None,
    include_items: Optional[bool] = None,
    raw: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Standard agent dispatcher entrypoint for Spotify.

    Args:
        action (str): 'current_track', 'playlists' or 'playlist'.
        limit (int): Page size for playlists or playlist items (1-50, default 10).
        offset (int): Index of the first playlist or playlist item to return (default 0).
        playlist_id (str): Playlist ID, URI or URL. Required for action 'playlist'.
        include_items (bool): For 'playlist', also fetch the playlist's tracks (default True).
        raw (bool): Return Spotify's unmodified JSON instead of a compact summary (default False).

    Returns:
        Dict[str, Any]: Result dictionary containing status and output data.
    """
    if action not in ACTIONS:
        return {
            "success": False,
            "error": f"Invalid action '{action}'. Must be one of: {', '.join(ACTIONS)}.",
        }

    try:
        limit = _int_param(limit, "limit", DEFAULT_LIMIT, 1, MAX_LIMIT)
        offset = _int_param(offset, "offset", 0, 0, MAX_OFFSET)
        include_items = _bool_param(include_items, "include_items", True)
        raw = _bool_param(raw, "raw", False)
        if action == "playlist":
            playlist_id = _parse_playlist_id(playlist_id)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    try:
        if action == "current_track":
            return _current_track(raw)
        if action == "playlists":
            return _playlists(limit, offset, raw)
        return _playlist(playlist_id, include_items, limit, offset, raw)

    except SpotifyError as e:
        result: Dict[str, Any] = {"success": False, "error": str(e)}
        if e.status is not None:
            result["status"] = e.status
        if e.retry_after is not None:
            result["retry_after_seconds"] = e.retry_after
        return result

    except urllib.error.URLError as e:
        return {"success": False, "error": f"Network connection error: {str(e.reason)}"}

    except (socket.timeout, TimeoutError):
        return {"success": False, "error": f"Request to Spotify timed out after {TIMEOUT} seconds."}

    except json.JSONDecodeError:
        return {"success": False, "error": "Spotify returned a response that is not valid JSON."}

    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


if __name__ == "__main__":
    import sys

    # Usage: python tool.py [current_track | playlists | playlist <playlist_id>]
    args = sys.argv[1:] or ["current_track"]
    call: Dict[str, Any] = {"action": args[0]}
    if args[0] == "playlist" and len(args) > 1:
        call["playlist_id"] = args[1]
    print(json.dumps(run_tool(**call), indent=2))
