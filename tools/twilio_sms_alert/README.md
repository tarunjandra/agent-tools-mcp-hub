# Twilio SMS Alert Tool

Send critical SMS notifications from AI agent workflows using the [Twilio Programmable Messaging API](https://www.twilio.com/docs/messaging/api).

## Features
- **Standard-library only**: uses Python `urllib` / `json` / `base64` (no extra packages).
- **Env-based secrets**: Account SID, Auth Token, and phone numbers never need to be hardcoded.
- **Graceful errors**: missing config, HTTP failures, and Twilio error payloads return structured `{success, error}` responses.

---

## Setup

1. Create a [Twilio account](https://www.twilio.com/try-twilio) and note your **Account SID** and **Auth Token**.
2. Buy or verify a Twilio phone number that can send SMS.
3. Export credentials (recommended):

```bash
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your_auth_token"
export TWILIO_FROM_NUMBER="+15551234567"
export TWILIO_TO_NUMBER="+15557654321"
```

No `pip install` is required — `requirements.txt` is empty on purpose.

---

## Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `message` | `string` | **Yes** | SMS body (max 1600 characters). |
| `to` | `string` | No* | Destination E.164 number. Defaults to `TWILIO_TO_NUMBER`. |
| `from` | `string` | No* | Twilio sender E.164 number. Defaults to `TWILIO_FROM_NUMBER`. |
| `account_sid` | `string` | No* | Twilio Account SID. Defaults to `TWILIO_ACCOUNT_SID`. |
| `auth_token` | `string` | No* | Twilio Auth Token. Defaults to `TWILIO_AUTH_TOKEN`. |

\*Required either as a parameter or via the matching environment variable.

---

## Usage Example

```python
from tool import send_sms_alert, run_tool

# Using environment variables for credentials / numbers
result = send_sms_alert(
    message="Critical agent alert: production deploy failed."
)
print(result)

# Or pass everything explicitly
result = run_tool(
    message="Disk usage exceeded 90% on api-1.",
    to="+15557654321",
    **{"from": "+15551234567"},
    account_sid="ACxxxxxxxx",
    auth_token="your_token",
)
print(result)
```

---

## Example Responses

### Success
```json
{
  "success": true,
  "message": "SMS alert queued successfully via Twilio.",
  "data": {
    "sid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "status": "queued",
    "to": "+15557654321",
    "from": "+15551234567",
    "date_created": "Fri, 21 Aug 2026 18:00:00 +0000",
    "error_code": null,
    "error_message": null
  }
}
```

### Missing credentials
```json
{
  "success": false,
  "error": "Twilio Account SID is required. Pass account_sid or set TWILIO_ACCOUNT_SID."
}
```
