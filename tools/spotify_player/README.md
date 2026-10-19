# 🎵 Spotify Player Tool

A tool that lets an agent see what the user is listening to on Spotify and read their playlists:

- **`current_track`**: the track or podcast episode playing right now, with progress and the playlist/album it's playing from.
- **`playlists`**: the user's playlists (public, private and collaborative), with paging.
- **`playlist`**: one playlist's details and tracks, by ID, URI or share link.

Results are compact summaries by default so they fit easily in an agent's context. Pass `raw=True` to get Spotify's full JSON instead.

No external dependencies: the tool only uses the Python standard library.

## Setup

This tool reads user-specific data, so it needs a **user** token from Spotify's Authorization Code flow. A Client Credentials (app-only) token won't work.

### 1. Create a Spotify app

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/) and create an app with the **Web API** enabled.
2. Under **Redirect URIs**, add `http://127.0.0.1:8888/callback`. Spotify doesn't accept `localhost` here; use `127.0.0.1`.
3. Note the app's **Client ID** and **Client Secret**.

> **Development Mode limits:** new Spotify apps run in Development Mode. The app owner must have **Spotify Premium**, and at most **5 Spotify users** can use the app. Each one must be added under **User Management** in the dashboard. See [Spotify's quota modes docs](https://developer.spotify.com/documentation/web-api/concepts/quota-modes).

### 2. Get a refresh token

Run the included helper once. It opens Spotify's consent page, catches the redirect on `127.0.0.1:8888`, and prints the variables to set:

```bash
export SPOTIFY_CLIENT_ID="your_client_id"
export SPOTIFY_CLIENT_SECRET="your_client_secret"
python tools/spotify_player/auth_helper.py
```

```text
Authorized. Add these to your environment:

export SPOTIFY_CLIENT_ID="your_client_id"
export SPOTIFY_CLIENT_SECRET="<your client secret>"
export SPOTIFY_REFRESH_TOKEN="AQB..."
```

If you leave `SPOTIFY_CLIENT_SECRET` unset, the helper uses the PKCE flow instead, and the tool can refresh tokens without a secret. To use a different redirect URI, register it in the dashboard and set `SPOTIFY_REDIRECT_URI`.

The helper requests these scopes:

| Scope | Needed for |
|---|---|
| `user-read-currently-playing` | `current_track` |
| `playlist-read-private` | private playlists in `playlists` and `playlist` |
| `playlist-read-collaborative` | collaborative playlists in `playlists` and `playlist` |

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `SPOTIFY_CLIENT_ID` | With refresh token | Your app's Client ID. |
| `SPOTIFY_REFRESH_TOKEN` | With refresh token | From `auth_helper.py`. Lets the tool get new access tokens on its own. Spotify refresh tokens last about 6 months. |
| `SPOTIFY_CLIENT_SECRET` | Unless you used PKCE | Your app's Client Secret. |
| `SPOTIFY_ACCESS_TOKEN` | Alternative | A user access token you already have. These expire after 1 hour and are not refreshed. Ignored when refresh credentials are set. |

When refresh credentials are set, the tool caches the access token in memory, refreshes it shortly before it expires, and retries a request once if Spotify rejects the token early. If Spotify issues a new refresh token, the tool uses it for the rest of the process, but it can't update your environment.

## Parameters

| Name | Type | Default | Description |
|---|---|---|---|
| `action` | string | required | `current_track`, `playlists` or `playlist`. |
| `playlist_id` | string | | Required for `playlist`. A playlist ID, `spotify:playlist:` URI, or `open.spotify.com` link. |
| `limit` | integer | `10` | Playlists (`playlists`) or tracks (`playlist`) per page, 1 to 50. |
| `offset` | integer | `0` | Where the page starts. Use `next_offset` from the previous result to get the next page. |
| `include_items` | boolean | `true` | For `playlist`: also fetch the tracks. |
| `raw` | boolean | `false` | Return Spotify's full JSON instead of the summary. |

## Usage (Python)

```python
import sys
sys.path.append("tools/spotify_player")
from tool import run_tool

# What's playing right now?
print(run_tool(action="current_track"))

# The user's playlists, 5 at a time
page = run_tool(action="playlists", limit=5)
print(page)
if page["success"] and page["data"]["next_offset"] is not None:
    print(run_tool(action="playlists", limit=5, offset=page["data"]["next_offset"]))

# One playlist's details and first 20 tracks
print(run_tool(action="playlist", playlist_id="https://open.spotify.com/playlist/3cEYpjA9oz9GiPac4AsH4n", limit=20))
```

From the command line:

```bash
python tools/spotify_player/tool.py current_track
python tools/spotify_player/tool.py playlists
python tools/spotify_player/tool.py playlist 3cEYpjA9oz9GiPac4AsH4n
```

## Example output

`current_track`:

```json
{
  "success": true,
  "data": {
    "is_playing": true,
    "progress_ms": 81234,
    "currently_playing_type": "track",
    "item": {
      "type": "track",
      "id": "4uLU6hMCjMI75M1A2tKUQC",
      "name": "Never Gonna Give You Up",
      "artists": ["Rick Astley"],
      "album": "Whenever You Need Somebody",
      "duration_ms": 213573,
      "explicit": false,
      "is_local": false,
      "url": "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
      "uri": "spotify:track:4uLU6hMCjMI75M1A2tKUQC"
    },
    "context": {
      "type": "playlist",
      "uri": "spotify:playlist:3cEYpjA9oz9GiPac4AsH4n",
      "url": "https://open.spotify.com/playlist/3cEYpjA9oz9GiPac4AsH4n"
    }
  }
}
```

When a podcast is playing, `item` has `"type": "episode"` with `show` and `release_date` instead of `artists` and `album`. When nothing is playing, `data` is `null` and `message` says so.

`playlists` returns `{"playlists": [...], "total", "limit", "offset", "next_offset"}`. Each playlist has `id`, `name`, `description`, `owner`, `owner_id`, `public`, `collaborative`, `item_count`, `image`, `url`, `uri` and `snapshot_id`.

`playlist` returns `{"playlist": {...}, "items": [...], "total", "limit", "offset", "next_offset"}`. Each entry in `items` has `added_at`, `added_by` and an `item` in the same format as `current_track`.

Errors return `{"success": false, "error": "..."}`, plus the HTTP `status` when Spotify returned one, and `retry_after_seconds` when Spotify is rate limiting.

## Notes on Spotify's 2026 API changes

Spotify changed its Web API in February 2026 ([changelog](https://developer.spotify.com/documentation/web-api/references/changes/february-2026)). This tool already follows the new rules:

- Playlist tracks come from `GET /playlists/{id}/items`. The old `/tracks` endpoint was removed.
- Spotify only returns tracks for the **user's own playlists**. For anyone else's playlist, `playlist` still returns the details, with `"items": null` and a `message` explaining why.
- Playlist responses renamed `tracks` to `items`, and `track` to `item`. The summaries handle both names. If you use `raw=True`, expect the new names.

Since [November 2024](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api), Development Mode apps also can't read Spotify-owned editorial and algorithmic playlists (such as Today's Top Hits or Discover Weekly). `playlist` returns a 404 error for these, with a note explaining why.

## Testing

The tests mock Spotify's API, so they need no credentials or network access:

```bash
python -m unittest discover -s tools/spotify_player -v
```
