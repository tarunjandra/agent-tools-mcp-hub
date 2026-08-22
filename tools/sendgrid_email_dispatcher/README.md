# SendGrid Email Dispatcher

Send plain-text or HTML emails using the SendGrid v3 Mail Send API.

## Features

- Send plain-text emails
- Send HTML emails
- Environment-based SendGrid authentication
- Configurable recipient and subject
- Structured API error handling
- MCP-compatible metadata

## Parameters

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `query` | string | Yes | Email body content |
| `to_email` | string | Yes | Recipient email address |
| `subject` | string | Yes | Email subject |
| `html` | boolean | No | Send body as HTML when `true`; defaults to `false` |

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `SENDGRID_API_KEY` | Yes | SendGrid API key with mail-send permission |
| `SENDGRID_FROM_EMAIL` | Yes | Verified SendGrid sender email address |

## Installation

```bash
pip install -r requirements.txt
```

## Plain-Text Example

```python
from tool import run_tool

result = run_tool(
    query="Hello from Agent Tools!",
    to_email="recipient@example.com",
    subject="Agent notification"
)

print(result)
```

## HTML Example

```python
from tool import run_tool

result = run_tool(
    query="<h1>Hello</h1><p>This message was sent from Agent Tools.</p>",
    to_email="recipient@example.com",
    subject="HTML notification",
    html=True
)

print(result)
```

## Example Success Response

```json
{
  "success": true,
  "status": 202,
  "message": "Email accepted by SendGrid."
}
```

## SendGrid Setup

The email address configured in `SENDGRID_FROM_EMAIL` must be authorized as a sender in SendGrid.

Configure credentials with environment variables rather than putting them directly in source code.

Example PowerShell setup:

```powershell
$env:SENDGRID_API_KEY="your_api_key"
$env:SENDGRID_FROM_EMAIL="verified-sender@example.com"
```

## Security

Never commit your SendGrid API key to GitHub.

Keep API credentials in environment variables or a secure secrets manager.