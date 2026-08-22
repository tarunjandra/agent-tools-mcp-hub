"""
Twilio SMS Alert Tool for AI Agents and MCP Hub.
Sends critical SMS notifications via the Twilio Programmable Messaging API.
"""
import os
import json
import base64
import urllib.parse
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

API_BASE = "https://api.twilio.com/2010-04-01"


def send_sms_alert(
    message: str,
    to: Optional[str] = None,
    from_: Optional[str] = None,
    account_sid: Optional[str] = None,
    auth_token: Optional[str] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Sends an SMS alert using Twilio's REST API.

    Args:
        message (str): SMS body text to deliver.
        to (str, optional): Destination phone number in E.164 format (e.g. +15551234567).
            Falls back to TWILIO_TO_NUMBER environment variable.
        from_ (str, optional): Twilio sender phone number or Messaging Service sender.
            Falls back to TWILIO_FROM_NUMBER environment variable.
            Also accepts kwargs key 'from' for agent-friendly parameter naming.
        account_sid (str, optional): Twilio Account SID.
            Falls back to TWILIO_ACCOUNT_SID environment variable.
        auth_token (str, optional): Twilio Auth Token.
            Falls back to TWILIO_AUTH_TOKEN environment variable.

    Returns:
        Dict[str, Any]: Result dictionary with success status, message SID / status, or error.
    """
    # Allow agents to pass `from` (reserved keyword in Python) via kwargs
    sender = from_ or kwargs.get("from") or os.getenv("TWILIO_FROM_NUMBER")
    recipient = to or os.getenv("TWILIO_TO_NUMBER")
    sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
    token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")

    if not sid:
        return {
            "success": False,
            "error": "Twilio Account SID is required. Pass account_sid or set TWILIO_ACCOUNT_SID."
        }

    if not token:
        return {
            "success": False,
            "error": "Twilio Auth Token is required. Pass auth_token or set TWILIO_AUTH_TOKEN."
        }

    if not recipient or not str(recipient).strip():
        return {
            "success": False,
            "error": "Destination number 'to' is required. Pass to or set TWILIO_TO_NUMBER."
        }

    if not sender or not str(sender).strip():
        return {
            "success": False,
            "error": "Sender number 'from' is required. Pass from_ / from or set TWILIO_FROM_NUMBER."
        }

    if not message or not str(message).strip():
        return {
            "success": False,
            "error": "Message parameter cannot be empty."
        }

    body = str(message).strip()
    if len(body) > 1600:
        return {
            "success": False,
            "error": "Message exceeds Twilio's 1600-character limit for a single SMS body."
        }

    url = f"{API_BASE}/Accounts/{sid}/Messages.json"
    form = urllib.parse.urlencode({
        "To": str(recipient).strip(),
        "From": str(sender).strip(),
        "Body": body,
    }).encode("utf-8")

    basic = base64.b64encode(f"{sid}:{token}".encode("utf-8")).decode("ascii")
    headers = {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "User-Agent": "AgentToolsHub/1.0 (https://github.com/tarunjandra/agent-tools-mcp-hub)",
    }

    try:
        req = urllib.request.Request(url, data=form, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))

        return {
            "success": True,
            "message": "SMS alert queued successfully via Twilio.",
            "data": {
                "sid": data.get("sid"),
                "status": data.get("status"),
                "to": data.get("to"),
                "from": data.get("from"),
                "date_created": data.get("date_created"),
                "error_code": data.get("error_code"),
                "error_message": data.get("error_message"),
            },
        }

    except urllib.error.HTTPError as e:
        error_msg = f"Twilio API HTTP {e.code}: {e.reason}"
        try:
            payload = json.loads(e.read().decode("utf-8", errors="replace"))
            detail = payload.get("message") or payload.get("error_message")
            code = payload.get("code") or payload.get("error_code")
            if detail and code:
                error_msg = f"Twilio API error {e.code} ({code}): {detail}"
            elif detail:
                error_msg = f"Twilio API error {e.code}: {detail}"
        except Exception:
            pass

        return {
            "success": False,
            "error": error_msg,
            "status_code": e.code,
        }

    except urllib.error.URLError as e:
        return {
            "success": False,
            "error": f"Network connection error: {str(e.reason)}",
        }

    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "Twilio returned a response that could not be parsed as JSON.",
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error while sending SMS via Twilio: {str(e)}",
        }


def run_tool(query: str = "", **kwargs: Any) -> Dict[str, Any]:
    """
    Standard agent dispatcher entrypoint.
    Accepts 'message' (or 'query' as fallback) plus Twilio routing / credential parameters.
    """
    message = kwargs.get("message") or query
    return send_sms_alert(
        message=message,
        to=kwargs.get("to"),
        from_=kwargs.get("from_") or kwargs.get("from"),
        account_sid=kwargs.get("account_sid"),
        auth_token=kwargs.get("auth_token"),
    )


if __name__ == "__main__":
    print("Twilio SMS Alert Tool loaded.")
    print("Without credentials the tool fails gracefully:")
    print(json.dumps(run_tool("Critical agent alert: pipeline failed"), indent=2))
