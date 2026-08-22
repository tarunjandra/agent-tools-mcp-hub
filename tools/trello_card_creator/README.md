# Trello Card Creator

Create task cards in specified Trello lists using the Trello REST API.

## Features

- Create Trello cards by list ID
- Configurable card title
- Optional card description
- Environment-based authentication
- Input validation
- Structured API error handling
- MCP-compatible metadata

## Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `query` | string | Yes | Title or name of the Trello card |
| `list_id` | string | Yes | Trello list ID where the card will be created |
| `description` | string | No | Optional card description |

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `TRELLO_API_KEY` | Yes | Trello API key |
| `TRELLO_TOKEN` | Yes | Trello API token |

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from tool import run_tool

result = run_tool(
    query="Follow up with client",
    list_id="YOUR_TRELLO_LIST_ID",
    description="Send the client a project update before Friday."
)

print(result)
```

## Example Success Response

```json
{
  "success": true,
  "status": 200,
  "data": {
    "id": "64abcd1234567890",
    "name": "Follow up with client",
    "description": "Send the client a project update before Friday.",
    "list_id": "60abcdef12345678",
    "url": "https://trello.com/c/example/follow-up-with-client",
    "short_url": "https://trello.com/c/example"
  }
}
```

## Authentication

Set your Trello credentials using environment variables.

PowerShell example:

```powershell
$env:TRELLO_API_KEY="your_api_key"
$env:TRELLO_TOKEN="your_token"
```

Do not place credentials directly in source code.

## Security

Never commit your Trello API key or token to GitHub.

Store credentials in environment variables or a secure secrets manager.