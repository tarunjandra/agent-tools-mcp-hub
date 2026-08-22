# Jira Ticket Status Fetcher

Fetch the status, summary, and description of a Jira Cloud issue using the Jira REST API v3.

## Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `query` | string | Yes | Jira issue key, for example `PROJ-123` |

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `JIRA_BASE_URL` | Yes | Jira Cloud site URL, e.g. `https://example.atlassian.net` |
| `JIRA_EMAIL` | Yes | Atlassian account email |
| `JIRA_API_TOKEN` | Yes | Atlassian API token |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from tool import run_tool

result = run_tool(
    query="PROJ-123"
)

print(result)
```

## Example Success Response

```json
{
  "success": true,
  "data": {
    "key": "PROJ-123",
    "summary": "Fix login issue",
    "status": "In Progress",
    "description": "Users are unable to log in."
  }
}
```

## Authentication

The tool uses Jira Cloud basic authentication with an Atlassian account email address and API token.

Never commit Jira credentials or API tokens to the repository.