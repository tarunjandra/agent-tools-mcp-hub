# GitHub Repository Stats & Releases (TypeScript)

Fetch public repository statistics **and release history** for any GitHub repository using the public **GitHub REST API**.

- **No API key required.** An optional `GITHUB_TOKEN` environment variable raises the rate limit (60 → 5,000 requests/hour).
- Returns release tags, publish dates, prerelease flags, asset counts and **total download counts** per release.
- Graceful handling of missing repos, invalid tokens, rate limits and network failures.

> Complements the existing Python [`github_repo_info`](../github_repo_info) tool, which covers repository metadata only. This TypeScript implementation adds release history and download metrics.

## Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `repo` | `string` | Yes | Repository in `owner/repo` format, e.g. `tarunjandra/agent-tools-mcp-hub`. A full GitHub URL is also accepted. |
| `action` | `string` | No | `stats`, `releases`, or `all` (default `all`) |
| `limit` | `integer` | No | Number of releases to return, 1–30 (default `5`) |

## Installation & Setup

```bash
cd tools/github_repo_stats_ts
npm install

# Optional, to raise the rate limit:
export GITHUB_TOKEN="ghp_xxx"
```

## Usage Example

```typescript
import { runTool } from "./index";

const result = await runTool("facebook/react", "all", 3);
console.log(result);
```

Run it directly from the command line:

```bash
npm start                          # defaults to tarunjandra/agent-tools-mcp-hub
npm start -- facebook/react        # any owner/repo
```

### Example output

```json
{
  "success": true,
  "data": {
    "stats": {
      "full_name": "octocat/Hello-World",
      "description": "My first repository on GitHub!",
      "language": "TypeScript",
      "stars": 1500,
      "forks": 230,
      "watchers": 44,
      "open_issues": 12,
      "license": "MIT",
      "topics": ["agents", "mcp"],
      "default_branch": "main",
      "archived": false,
      "created_at": "2020-01-15",
      "pushed_at": "2026-08-19",
      "repo_url": "https://github.com/octocat/Hello-World"
    },
    "latest_release": {
      "tag": "v2.1.0",
      "name": "Release 2.1.0",
      "published_at": "2026-07-01",
      "is_prerelease": false,
      "is_draft": false,
      "author": "octocat",
      "asset_count": 2,
      "total_downloads": 500,
      "release_url": "https://github.com/octocat/Hello-World/releases/tag/v2.1.0"
    },
    "releases": [
      {
        "tag": "v2.1.0",
        "name": "Release 2.1.0",
        "published_at": "2026-07-01",
        "is_prerelease": false,
        "is_draft": false,
        "author": "octocat",
        "asset_count": 2,
        "total_downloads": 500,
        "release_url": "https://github.com/octocat/Hello-World/releases/tag/v2.1.0"
      },
      {
        "tag": "v2.0.0",
        "name": "Release 2.0.0",
        "published_at": "2026-05-12",
        "is_prerelease": false,
        "is_draft": false,
        "author": "octocat",
        "asset_count": 3,
        "total_downloads": 1240,
        "release_url": "https://github.com/octocat/Hello-World/releases/tag/v2.0.0"
      }
    ],
    "release_count": 2
  }
}
```

### Error output

Errors are returned as data rather than thrown, so an agent can read and act on them:

```json
{
  "success": false,
  "error": "GitHub API rate limit exceeded (resets at 2026-08-21T21:39:18.000Z). Set a GITHUB_TOKEN environment variable to raise the limit from 60 to 5,000 requests/hour."
}
```

## Notes

- A repository with no published releases returns `latest_release: null` with `success: true` — an empty release list is a valid result, not an error.
- `watchers` uses GitHub's `subscribers_count` (people actually watching), not `watchers_count`, which the API returns as a duplicate of the star count.
- Draft releases are included in `releases` but excluded from `latest_release`.
- `latest_release` is the most recent non-draft release, which **includes prereleases**. This differs from GitHub's own `/releases/latest` endpoint, which excludes prereleases as well as drafts — check `is_prerelease` if you need the latest stable release only.
- `action: "all"` issues **two** API requests (one for stats, one for releases). Unauthenticated, that allows roughly 30 `all` calls per hour against the 60 requests/hour limit; set `GITHUB_TOKEN` to raise the ceiling to 5,000.
