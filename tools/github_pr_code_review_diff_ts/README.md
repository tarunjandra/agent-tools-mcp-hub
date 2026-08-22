# GitHub PR Code Review Diff Tool (TypeScript)

Fetches the changed files and patch details for an open GitHub pull request. The result is structured for automated AI/code-review workflows.

## Features

- Accepts a full GitHub pull request URL or `owner` + `repo` + `pull_number`
- Returns pull request title and state
- Returns changed filenames, status, additions, deletions, and patch content
- Uses the GitHub REST API
- Supports `GITHUB_TOKEN` through the environment without hardcoding credentials
- Rejects closed or merged pull requests

## Installation

```bash
npm install
```

## Usage

```typescript
import { getPullRequestDiff } from "./index";

const result = await getPullRequestDiff(
  "https://github.com/tarunjandra/agent-tools-mcp-hub/pull/1",
);

console.log(JSON.stringify(result, null, 2));
```

Or provide repository details:

```typescript
const result = await getPullRequestDiff(
  undefined,
  "tarunjandra",
  "agent-tools-mcp-hub",
  1,
);
```

For authenticated requests, set:

```bash
export GITHUB_TOKEN="your-token"
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pull_request_url` | string | Conditional | Full GitHub pull request URL |
| `owner` | string | Conditional | Repository owner |
| `repo` | string | Conditional | Repository name |
| `pull_number` | integer | Conditional | Pull request number |
| `token` | string | No | GitHub token; falls back to `GITHUB_TOKEN` |

Provide either `pull_request_url` or all three of `owner`, `repo`, and `pull_number`.

## Output

A successful response includes:

- Repository and pull request number
- Pull request title and state
- Number of changed files
- Each changed file's path, status, additions, deletions, changes, and patch

## API

Uses GitHub's pull request REST endpoints:

- `GET /repos/{owner}/{repo}/pulls/{pull_number}`
- `GET /repos/{owner}/{repo}/pulls/{pull_number}/files`
