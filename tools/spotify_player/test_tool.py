"""
Offline tests for the Spotify Player tool. Run with:
    python -m unittest discover -s tools/spotify_player -v
"""
import base64
import io
import json
import os
import socket
import sys
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import auth_helper  # noqa: E402
import tool  # noqa: E402

TRACK = {
    "type": "track",
    "id": "t1",
    "name": "Song",
    "artists": [{"name": "Artist A"}, {"name": "Artist B"}],
    "album": {"name": "Album", "images": [{"url": "https://img"}]},
    "duration_ms": 200000,
    "explicit": False,
    "is_local": False,
    "popularity": 50,
    "available_markets": ["US"],
    "external_urls": {"spotify": "https://open.spotify.com/track/t1"},
    "uri": "spotify:track:t1",
}
EPISODE = {
    "type": "episode",
    "id": "e1",
    "name": "Episode",
    "show": {"name": "Podcast"},
    "duration_ms": 3600000,
    "release_date": "2026-10-01",
    "explicit": True,
    "external_urls": {"spotify": "https://open.spotify.com/episode/e1"},
    "uri": "spotify:episode:e1",
}
PLAYLIST = {
    "id": "37i9dQZF1DXcBWIGoYBM5M",
    "name": "Mix",
    "description": "desc",
    "owner": {"id": "owner1", "display_name": "Owner"},
    "public": True,
    "collaborative": False,
    "items": {"href": "https://api.spotify.com/v1/playlists/x/items", "total": 42},
    "images": [{"url": "https://cover"}],
    "external_urls": {"spotify": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"},
    "uri": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",
    "snapshot_id": "snap",
}


class FakeResponse:
    def __init__(self, status: int = 200, body: Any = None):
        self.status = status
        self._body = b"" if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        pass


def http_error(url: str, code: int, body: Any = None, headers: Optional[Dict[str, str]] = None) -> urllib.error.HTTPError:
    data = json.dumps(body).encode() if body is not None else b""
    return urllib.error.HTTPError(url, code, "reason", headers or {}, io.BytesIO(data))


class FakeSpotify:
    """Routes urlopen calls by URL prefix; each route is a list of responses/exceptions served in order."""

    def __init__(self, routes: Dict[str, List[Any]]):
        self.routes = {prefix: list(responses) for prefix, responses in routes.items()}
        self.requests: List[urllib.request.Request] = []

    def __call__(self, req: urllib.request.Request, timeout: float = None) -> FakeResponse:
        self.requests.append(req)
        for prefix in sorted(self.routes, key=len, reverse=True):
            if req.full_url.startswith(prefix):
                outcome = self.routes[prefix].pop(0)
                if isinstance(outcome, BaseException):
                    raise outcome
                return outcome
        raise AssertionError(f"Unexpected request: {req.full_url}")

    def urls(self) -> List[str]:
        return [r.full_url for r in self.requests]

    def query(self, index: int) -> Dict[str, str]:
        return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.requests[index].full_url).query))


API = tool.API_BASE
CURRENT = f"{API}/me/player/currently-playing"
PLAYLISTS = f"{API}/me/playlists"
ACCESS_ENV = {"SPOTIFY_ACCESS_TOKEN": "static-token"}
REFRESH_ENV = {"SPOTIFY_CLIENT_ID": "cid", "SPOTIFY_CLIENT_SECRET": "secret", "SPOTIFY_REFRESH_TOKEN": "rt1"}


class SpotifyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tool._token_cache.update(key=None, access_token=None, expires_at=0.0, refresh_token=None)

    def run_with(self, env: Dict[str, str], routes: Dict[str, List[Any]], **kwargs: Any):
        fake = FakeSpotify(routes)
        with mock.patch.dict(os.environ, env, clear=True), mock.patch("urllib.request.urlopen", fake):
            return tool.run_tool(**kwargs), fake


class ValidationTests(SpotifyTestCase):
    def test_missing_credentials(self):
        result, fake = self.run_with({}, {}, action="current_track")
        self.assertFalse(result["success"])
        self.assertIn("SPOTIFY_ACCESS_TOKEN", result["error"])
        self.assertEqual(fake.requests, [])

    def test_invalid_action(self):
        for action in ("bogus", None, ""):
            result, _ = self.run_with(ACCESS_ENV, {}, action=action)
            self.assertFalse(result["success"])
            self.assertIn("Invalid action", result["error"])

    def test_limit_none_uses_default(self):
        result, fake = self.run_with(ACCESS_ENV, {PLAYLISTS: [FakeResponse(body={"items": []})]}, action="playlists", limit=None)
        self.assertTrue(result["success"])
        self.assertEqual(fake.query(0), {"limit": "10", "offset": "0"})

    def test_limit_accepts_numeric_strings_and_whole_floats(self):
        for value, expected in (("5", "5"), (5.0, "5"), (50, "50"), (1, "1")):
            result, fake = self.run_with(ACCESS_ENV, {PLAYLISTS: [FakeResponse(body={"items": []})]}, action="playlists", limit=value)
            self.assertTrue(result["success"], value)
            self.assertEqual(fake.query(0)["limit"], expected)

    def test_limit_rejects_bad_values_without_calling_spotify(self):
        for value in (True, False, 2.9, 0, 51, 500, -1, "abc", [5]):
            result, fake = self.run_with(ACCESS_ENV, {}, action="playlists", limit=value)
            self.assertFalse(result["success"], value)
            self.assertIn("limit", result["error"])
            self.assertEqual(fake.requests, [])

    def test_offset_bounds(self):
        for value in (-1, 100001, "x"):
            result, _ = self.run_with(ACCESS_ENV, {}, action="playlists", offset=value)
            self.assertFalse(result["success"], value)
            self.assertIn("offset", result["error"])

    def test_bool_params(self):
        result, _ = self.run_with(ACCESS_ENV, {}, action="playlists", raw="maybe")
        self.assertFalse(result["success"])
        self.assertIn("raw", result["error"])

    def test_playlist_id_formats(self):
        expected = "37i9dQZF1DXcBWIGoYBM5M"
        for value in (
            expected,
            f"  {expected}  ",
            f"spotify:playlist:{expected}",
            f"spotify:user:someone:playlist:{expected}",
            f"https://open.spotify.com/playlist/{expected}?si=abc123",
            f"https://open.spotify.com/intl-de/playlist/{expected}",
        ):
            self.assertEqual(tool._parse_playlist_id(value), expected, value)

    def test_playlist_id_required_and_validated(self):
        for value in (None, "", "   ", "bad id!", "../me"):
            result, fake = self.run_with(ACCESS_ENV, {}, action="playlist", playlist_id=value)
            self.assertFalse(result["success"], value)
            self.assertIn("playlist_id", result["error"])
            self.assertEqual(fake.requests, [])


class CurrentTrackTests(SpotifyTestCase):
    def test_track_summary_and_episode_support_requested(self):
        body = {
            "is_playing": True,
            "progress_ms": 1234,
            "currently_playing_type": "track",
            "item": TRACK,
            "context": {"type": "playlist", "uri": "spotify:playlist:p", "external_urls": {"spotify": "https://p"}},
            "actions": {"disallows": {}},
        }
        result, fake = self.run_with(ACCESS_ENV, {CURRENT: [FakeResponse(body=body)]}, action="current_track")
        self.assertTrue(result["success"])
        self.assertEqual(fake.query(0), {"additional_types": "track,episode"})
        self.assertEqual(fake.requests[0].get_header("Authorization"), "Bearer static-token")
        self.assertEqual(result["data"], {
            "is_playing": True,
            "progress_ms": 1234,
            "currently_playing_type": "track",
            "item": {
                "type": "track",
                "id": "t1",
                "name": "Song",
                "artists": ["Artist A", "Artist B"],
                "album": "Album",
                "duration_ms": 200000,
                "explicit": False,
                "is_local": False,
                "url": "https://open.spotify.com/track/t1",
                "uri": "spotify:track:t1",
            },
            "context": {"type": "playlist", "uri": "spotify:playlist:p", "url": "https://p"},
        })

    def test_episode_summary(self):
        body = {"is_playing": True, "progress_ms": 5, "currently_playing_type": "episode", "item": EPISODE, "context": None}
        result, _ = self.run_with(ACCESS_ENV, {CURRENT: [FakeResponse(body=body)]}, action="current_track")
        item = result["data"]["item"]
        self.assertEqual(item["type"], "episode")
        self.assertEqual(item["show"], "Podcast")
        self.assertIsNone(result["data"]["context"])
        self.assertNotIn("message", result)

    def test_nothing_playing(self):
        for response in (FakeResponse(status=204), FakeResponse(status=200, body=b"  ")):
            result, _ = self.run_with(ACCESS_ENV, {CURRENT: [response]}, action="current_track")
            self.assertEqual(result, {"success": True, "data": None, "message": "No track is currently playing."})

    def test_ad_playing_has_message(self):
        body = {"is_playing": True, "currently_playing_type": "ad", "item": None}
        result, _ = self.run_with(ACCESS_ENV, {CURRENT: [FakeResponse(body=body)]}, action="current_track")
        self.assertTrue(result["success"])
        self.assertIsNone(result["data"]["item"])
        self.assertIn("ad", result["message"])

    def test_raw_returns_unmodified_json(self):
        body = {"is_playing": True, "currently_playing_type": "track", "item": TRACK}
        result, _ = self.run_with(ACCESS_ENV, {CURRENT: [FakeResponse(body=body)]}, action="current_track", raw=True)
        self.assertEqual(result["data"], body)


class PlaylistsTests(SpotifyTestCase):
    def test_summary_and_pagination(self):
        page = {"items": [PLAYLIST, None], "total": 25, "limit": 2, "offset": 4, "next": "https://next"}
        result, fake = self.run_with(ACCESS_ENV, {PLAYLISTS: [FakeResponse(body=page)]}, action="playlists", limit=2, offset=4)
        self.assertEqual(fake.query(0), {"limit": "2", "offset": "4"})
        data = result["data"]
        self.assertEqual((data["total"], data["limit"], data["offset"], data["next_offset"]), (25, 2, 4, 6))
        self.assertEqual(len(data["playlists"]), 1)
        self.assertEqual(data["playlists"][0], {
            "id": "37i9dQZF1DXcBWIGoYBM5M",
            "name": "Mix",
            "description": "desc",
            "owner": "Owner",
            "owner_id": "owner1",
            "public": True,
            "collaborative": False,
            "item_count": 42,
            "image": "https://cover",
            "url": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M",
            "uri": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",
            "snapshot_id": "snap",
        })

    def test_last_page_has_no_next_offset(self):
        page = {"items": [], "total": 0, "next": None}
        result, _ = self.run_with(ACCESS_ENV, {PLAYLISTS: [FakeResponse(body=page)]}, action="playlists")
        self.assertIsNone(result["data"]["next_offset"])

    def test_legacy_tracks_field_still_counted(self):
        legacy = dict(PLAYLIST)
        legacy.pop("items")
        legacy["tracks"] = {"href": "x", "total": 7}
        legacy["owner"] = {"id": "only-id"}
        legacy["images"] = None
        summary = tool._summarize_playlist(legacy)
        self.assertEqual((summary["item_count"], summary["owner"], summary["image"]), (7, "only-id", None))


class PlaylistTests(SpotifyTestCase):
    PID = "37i9dQZF1DXcBWIGoYBM5M"

    def routes(self, items_outcome: Any) -> Dict[str, List[Any]]:
        return {
            f"{API}/playlists/{self.PID}": [FakeResponse(body=PLAYLIST)],
            f"{API}/playlists/{self.PID}/items": [items_outcome],
        }

    def test_metadata_and_items(self):
        page = {
            "items": [
                {"added_at": "2026-01-01T00:00:00Z", "added_by": {"id": "u1"}, "item": TRACK},
                {"added_at": "2026-01-02T00:00:00Z", "added_by": None, "track": EPISODE},  # pre-2026 shape
                None,
            ],
            "total": 42,
            "next": "https://next",
        }
        url = f"https://open.spotify.com/playlist/{self.PID}?si=x"
        result, fake = self.run_with(ACCESS_ENV, self.routes(FakeResponse(body=page)), action="playlist", playlist_id=url, limit=2)
        self.assertEqual(fake.urls()[0], f"{API}/playlists/{self.PID}")
        self.assertEqual(fake.query(1), {"limit": "2", "offset": "0", "additional_types": "track,episode"})
        data = result["data"]
        self.assertEqual(data["playlist"]["name"], "Mix")
        self.assertEqual([e["item"]["id"] for e in data["items"]], ["t1", "e1"])
        self.assertEqual(data["items"][0]["added_by"], "u1")
        self.assertIsNone(data["items"][1]["added_by"])
        self.assertEqual((data["total"], data["next_offset"]), (42, 2))

    def test_include_items_false_makes_one_call(self):
        result, fake = self.run_with(ACCESS_ENV, self.routes(None), action="playlist", playlist_id=self.PID, include_items="false")
        self.assertTrue(result["success"])
        self.assertEqual(len(fake.requests), 1)
        self.assertNotIn("items", result["data"])

    def test_items_forbidden_returns_metadata_only(self):
        forbidden = http_error("u", 403, {"error": {"status": 403, "message": "Forbidden"}})
        result, _ = self.run_with(ACCESS_ENV, self.routes(forbidden), action="playlist", playlist_id=self.PID)
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["playlist"]["id"], self.PID)
        self.assertIsNone(result["data"]["items"])
        self.assertIn("own playlists", result["message"])

    def test_items_other_errors_fail(self):
        result, _ = self.run_with(ACCESS_ENV, self.routes(http_error("u", 500)), action="playlist", playlist_id=self.PID)
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], 500)

    def test_playlist_not_found(self):
        routes = {f"{API}/playlists/{self.PID}": [http_error("u", 404, {"error": {"status": 404, "message": "Resource not found"}})]}
        result, _ = self.run_with(ACCESS_ENV, routes, action="playlist", playlist_id=self.PID)
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], 404)
        self.assertTrue(result["error"].startswith("Not found - Resource not found."))
        self.assertIn("Discover Weekly", result["error"])

    def test_raw(self):
        page = {"items": [{"item": TRACK}], "total": 1}
        result, _ = self.run_with(ACCESS_ENV, self.routes(FakeResponse(body=page)), action="playlist", playlist_id=self.PID, raw=True)
        self.assertEqual(result["data"], {"playlist": PLAYLIST, "items": page})


class ErrorHandlingTests(SpotifyTestCase):
    def test_401_includes_spotify_message(self):
        err = http_error(CURRENT, 401, {"error": {"status": 401, "message": "The access token expired"}})
        result, fake = self.run_with(ACCESS_ENV, {CURRENT: [err]}, action="current_track")
        self.assertEqual(result["error"], "Unauthorized: invalid or expired access token - The access token expired")
        self.assertEqual(len(fake.requests), 1)  # no refresh credentials, so no retry

    def test_429_surfaces_retry_after(self):
        err = http_error(CURRENT, 429, headers={"Retry-After": "17"})
        result, _ = self.run_with(ACCESS_ENV, {CURRENT: [err]}, action="current_track")
        self.assertEqual(result["status"], 429)
        self.assertEqual(result["retry_after_seconds"], 17)
        self.assertIn("Retry after 17 seconds", result["error"])

    def test_429_without_header(self):
        result, _ = self.run_with(ACCESS_ENV, {CURRENT: [http_error(CURRENT, 429)]}, action="current_track")
        self.assertNotIn("retry_after_seconds", result)

    def test_unknown_status_and_non_json_body(self):
        err = urllib.error.HTTPError(CURRENT, 502, "Bad Gateway", {}, io.BytesIO(b"<html>"))
        result, _ = self.run_with(ACCESS_ENV, {CURRENT: [err]}, action="current_track")
        self.assertEqual(result["error"], "HTTP Error 502: Bad Gateway")

    def test_network_timeout_and_bad_json(self):
        cases = (
            (urllib.error.URLError("no route"), "Network connection error: no route"),
            (socket.timeout("timed out"), "timed out"),
            (FakeResponse(body=b"{not json"), "not valid JSON"),
        )
        for outcome, expected in cases:
            result, _ = self.run_with(ACCESS_ENV, {CURRENT: [outcome]}, action="current_track")
            self.assertFalse(result["success"])
            self.assertIn(expected, result["error"])


class RefreshTokenTests(SpotifyTestCase):
    def token_response(self, access: str, refresh: Optional[str] = None, expires_in: int = 3600) -> FakeResponse:
        body = {"access_token": access, "token_type": "Bearer", "expires_in": expires_in}
        if refresh:
            body["refresh_token"] = refresh
        return FakeResponse(body=body)

    def test_refresh_with_client_secret_and_caching(self):
        fake = FakeSpotify({
            tool.TOKEN_URL: [self.token_response("fresh")],
            CURRENT: [FakeResponse(status=204), FakeResponse(status=204)],
        })
        env = dict(REFRESH_ENV, SPOTIFY_ACCESS_TOKEN="ignored")
        with mock.patch.dict(os.environ, env, clear=True), mock.patch("urllib.request.urlopen", fake):
            tool.run_tool(action="current_track")
            tool.run_tool(action="current_track")

        token_req, api_req, api_req2 = fake.requests
        self.assertEqual(token_req.get_method(), "POST")
        expected_basic = base64.b64encode(b"cid:secret").decode()
        self.assertEqual(token_req.get_header("Authorization"), f"Basic {expected_basic}")
        self.assertEqual(dict(urllib.parse.parse_qsl(token_req.data.decode())), {"grant_type": "refresh_token", "refresh_token": "rt1"})
        self.assertEqual(api_req.get_header("Authorization"), "Bearer fresh")
        self.assertEqual(api_req2.get_header("Authorization"), "Bearer fresh")

    def test_pkce_refresh_sends_client_id_without_secret(self):
        env = {"SPOTIFY_CLIENT_ID": "cid", "SPOTIFY_REFRESH_TOKEN": "rt1"}
        result, fake = self.run_with(env, {tool.TOKEN_URL: [self.token_response("fresh")], CURRENT: [FakeResponse(status=204)]}, action="current_track")
        self.assertTrue(result["success"])
        token_req = fake.requests[0]
        self.assertIsNone(token_req.get_header("Authorization"))
        self.assertEqual(dict(urllib.parse.parse_qsl(token_req.data.decode()))["client_id"], "cid")

    def test_expired_cache_refreshes_with_rotated_token(self):
        fake = FakeSpotify({
            tool.TOKEN_URL: [self.token_response("a1", refresh="rt2", expires_in=30), self.token_response("a2")],
            CURRENT: [FakeResponse(status=204), FakeResponse(status=204)],
        })
        with mock.patch.dict(os.environ, REFRESH_ENV, clear=True), mock.patch("urllib.request.urlopen", fake):
            tool.run_tool(action="current_track")  # expires_in=30 is inside the 60s safety margin
            tool.run_tool(action="current_track")
        second_refresh = dict(urllib.parse.parse_qsl(fake.requests[2].data.decode()))
        self.assertEqual(second_refresh["refresh_token"], "rt2")
        self.assertEqual(fake.requests[3].get_header("Authorization"), "Bearer a2")

    def test_changed_env_credentials_ignore_cache(self):
        fake = FakeSpotify({
            tool.TOKEN_URL: [self.token_response("a1", refresh="rotated"), self.token_response("b1")],
            CURRENT: [FakeResponse(status=204), FakeResponse(status=204)],
        })
        with mock.patch("urllib.request.urlopen", fake):
            with mock.patch.dict(os.environ, REFRESH_ENV, clear=True):
                tool.run_tool(action="current_track")
            with mock.patch.dict(os.environ, dict(REFRESH_ENV, SPOTIFY_REFRESH_TOKEN="other"), clear=True):
                tool.run_tool(action="current_track")
        self.assertEqual(dict(urllib.parse.parse_qsl(fake.requests[2].data.decode()))["refresh_token"], "other")
        self.assertEqual(fake.requests[3].get_header("Authorization"), "Bearer b1")

    def test_401_triggers_one_refresh_and_retry(self):
        unauthorized = http_error(CURRENT, 401, {"error": {"status": 401, "message": "revoked"}})
        routes = {
            tool.TOKEN_URL: [self.token_response("a1"), self.token_response("a2")],
            CURRENT: [unauthorized, FakeResponse(status=204)],
        }
        result, fake = self.run_with(REFRESH_ENV, routes, action="current_track")
        self.assertTrue(result["success"])
        self.assertEqual(fake.requests[3].get_header("Authorization"), "Bearer a2")

    def test_repeated_401_gives_up(self):
        def unauthorized():
            return http_error(CURRENT, 401, {"error": {"status": 401, "message": "nope"}})
        routes = {
            tool.TOKEN_URL: [self.token_response("a1"), self.token_response("a2")],
            CURRENT: [unauthorized(), unauthorized()],
        }
        result, fake = self.run_with(REFRESH_ENV, routes, action="current_track")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], 401)
        self.assertEqual(len(fake.requests), 4)

    def test_refresh_errors(self):
        cases = (
            ({"error": "invalid_grant", "error_description": "Refresh token revoked"}, "auth_helper.py"),
            ({"error": "invalid_client"}, "SPOTIFY_CLIENT_SECRET"),
            ({"error": "server_error", "error_description": "boom"}, "Token refresh failed: HTTP 400 - boom"),
        )
        for body, expected in cases:
            tool._token_cache.update(key=None, access_token=None, expires_at=0.0, refresh_token=None)
            routes = {tool.TOKEN_URL: [http_error(tool.TOKEN_URL, 400, body)]}
            result, _ = self.run_with(REFRESH_ENV, routes, action="current_track")
            self.assertFalse(result["success"])
            self.assertIn(expected, result["error"])


class AuthHelperTests(unittest.TestCase):
    def test_pkce_pair(self):
        verifier, challenge = auth_helper.pkce_pair()
        import hashlib
        digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        self.assertEqual(challenge, digest)
        self.assertTrue(43 <= len(verifier) <= 128)

    def test_authorize_url(self):
        url = auth_helper.build_authorize_url("cid", "http://127.0.0.1:8888/callback", "st", "chal")
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        self.assertEqual(query["scope"], "user-read-currently-playing playlist-read-private playlist-read-collaborative")
        self.assertEqual((query["code_challenge"], query["code_challenge_method"]), ("chal", "S256"))
        no_pkce = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(auth_helper.build_authorize_url("cid", "r", "st")).query))
        self.assertNotIn("code_challenge", no_pkce)

    def test_rejects_non_loopback_redirect(self):
        for uri in ("http://localhost:8888/callback", "https://127.0.0.1:8888/callback"):
            with self.assertRaises(ValueError):
                auth_helper.wait_for_code(uri, "st", timeout=1)

    def _callback_round_trip(self, query: str, state: str = "st") -> Any:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        redirect = f"http://127.0.0.1:{port}/callback"
        outcome: Dict[str, Any] = {}

        def serve() -> None:
            try:
                outcome["code"] = auth_helper.wait_for_code(redirect, state, timeout=10)
            except Exception as e:
                outcome["error"] = e

        thread = threading.Thread(target=serve)
        thread.start()
        for _ in range(50):  # wait for the server to bind
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/favicon.ico", timeout=1):
                    pass
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 404)
                break
            except urllib.error.URLError:
                threading.Event().wait(0.05)
        with urllib.request.urlopen(f"{redirect}?{query}", timeout=5) as response:
            self.assertIn(b"You can close this tab", response.read())
        thread.join(10)
        return outcome

    def test_local_callback_server_receives_code(self):
        self.assertEqual(self._callback_round_trip("code=abc&state=st"), {"code": "abc"})

    def test_local_callback_state_mismatch_and_denied(self):
        self.assertIn("State mismatch", str(self._callback_round_trip("code=abc&state=evil")["error"]))
        self.assertIn("access_denied", str(self._callback_round_trip("error=access_denied&state=st")["error"]))

    def test_exchange_code(self):
        fake = FakeSpotify({tool.TOKEN_URL: [FakeResponse(body={"access_token": "a", "refresh_token": "r"})]})
        with mock.patch("urllib.request.urlopen", fake):
            tokens = auth_helper.exchange_code("code1", "cid", None, "http://127.0.0.1:8888/callback", "ver")
        self.assertEqual(tokens["refresh_token"], "r")
        form = dict(urllib.parse.parse_qsl(fake.requests[0].data.decode()))
        self.assertEqual(form, {
            "grant_type": "authorization_code",
            "code": "code1",
            "redirect_uri": "http://127.0.0.1:8888/callback",
            "client_id": "cid",
            "code_verifier": "ver",
        })

    def test_exchange_code_error(self):
        fake = FakeSpotify({tool.TOKEN_URL: [http_error(tool.TOKEN_URL, 400, {"error": "invalid_grant", "error_description": "Invalid redirect URI"})]})
        with mock.patch("urllib.request.urlopen", fake), self.assertRaises(RuntimeError) as ctx:
            auth_helper.exchange_code("code1", "cid", "secret", "http://127.0.0.1:8888/callback")
        self.assertIn("Invalid redirect URI", str(ctx.exception))
        self.assertTrue(fake.requests[0].get_header("Authorization").startswith("Basic "))


if __name__ == "__main__":
    unittest.main()
