"""
One-time helper that authorizes the Spotify Player tool and prints a refresh token.

Usage:
    export SPOTIFY_CLIENT_ID="..."
    export SPOTIFY_CLIENT_SECRET="..."   # optional; PKCE is used when it is not set
    python tools/spotify_player/auth_helper.py

The redirect URI (default http://127.0.0.1:8888/callback, override with
SPOTIFY_REDIRECT_URI) must be registered in your app's settings on the Spotify
Developer Dashboard. Spotify does not accept "localhost" as a redirect URI.
"""
import base64
import hashlib
import http.server
import json
import os
import secrets
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from typing import Any, Dict, Optional, Tuple

from tool import SCOPES, TIMEOUT, TOKEN_URL, USER_AGENT

AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"


class _HTTPServerV6(http.server.HTTPServer):
    address_family = socket.AF_INET6


def pkce_pair() -> Tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge.decode("ascii").rstrip("=")


def build_authorize_url(client_id: str, redirect_uri: str, state: str, code_challenge: Optional[str] = None) -> str:
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(SCOPES),
        "state": state,
    }
    if code_challenge:
        params.update(code_challenge_method="S256", code_challenge=code_challenge)
    return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def wait_for_code(redirect_uri: str, state: str, timeout: float = 300) -> str:
    """Serves the redirect URI on the loopback address until Spotify sends the user back."""
    parsed = urllib.parse.urlparse(redirect_uri)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "::1"):
        raise ValueError("Redirect URI must be an http loopback address such as http://127.0.0.1:8888/callback.")
    callback: Dict[str, str] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            url = urllib.parse.urlparse(self.path)
            if url.path != (parsed.path or "/"):
                self.send_error(404)
                return
            callback.update({k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<p>Spotify authorization received. You can close this tab.</p>")

        def log_message(self, *args: Any) -> None:
            pass

    server_class = _HTTPServerV6 if parsed.hostname == "::1" else http.server.HTTPServer
    server = server_class((parsed.hostname, parsed.port or 80), Handler)
    server.timeout = 1
    deadline = time.time() + timeout
    try:
        while not callback and time.time() < deadline:
            server.handle_request()
    finally:
        server.server_close()

    if not callback:
        raise TimeoutError("Timed out waiting for Spotify to redirect back.")
    if callback.get("state") != state:
        raise ValueError("State mismatch in the Spotify callback; aborting.")
    if "error" in callback:
        raise ValueError(f"Spotify authorization failed: {callback['error']}")
    if "code" not in callback:
        raise ValueError("Spotify callback did not include an authorization code.")
    return callback["code"]


def exchange_code(
    code: str,
    client_id: str,
    client_secret: Optional[str],
    redirect_uri: str,
    code_verifier: Optional[str] = None,
) -> Dict[str, Any]:
    form = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri}
    headers = {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": USER_AGENT}
    if client_secret:
        basic = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {basic}"
    else:
        form.update(client_id=client_id, code_verifier=code_verifier or "")

    req = urllib.request.Request(
        TOKEN_URL, data=urllib.parse.urlencode(form).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
            detail = body.get("error_description") or body.get("error")
        except Exception:
            detail = None
        raise RuntimeError(f"Token exchange failed: HTTP {e.code}" + (f" - {detail}" if detail else "")) from None


def main() -> int:
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    if not client_id:
        print("Set SPOTIFY_CLIENT_ID (and optionally SPOTIFY_CLIENT_SECRET) first.", file=sys.stderr)
        return 1
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", DEFAULT_REDIRECT_URI)

    state = secrets.token_urlsafe(16)
    verifier, challenge = pkce_pair() if not client_secret else (None, None)
    url = build_authorize_url(client_id, redirect_uri, state, challenge)

    print("Open this URL to authorize (trying to open your browser automatically):\n")
    print(url + "\n")
    webbrowser.open(url)

    try:
        code = wait_for_code(redirect_uri, state)
        tokens = exchange_code(code, client_id, client_secret, redirect_uri, verifier)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print("Authorized. Add these to your environment:\n")
    print(f'export SPOTIFY_CLIENT_ID="{client_id}"')
    if client_secret:
        print('export SPOTIFY_CLIENT_SECRET="<your client secret>"')
    print(f'export SPOTIFY_REFRESH_TOKEN="{tokens.get("refresh_token", "")}"')
    print(f"\nGranted scopes: {tokens.get('scope', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
