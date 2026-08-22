"""
SendGrid Email Dispatcher

Sends plain-text or HTML emails using the SendGrid v3 Mail Send API.
"""

import os
from typing import Any, Dict

import requests


SENDGRID_MAIL_URL = "https://api.sendgrid.com/v3/mail/send"


def run_tool(query: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Send an email through SendGrid.

    Args:
        query (str): Email body content.
        to_email (str): Recipient email address.
        subject (str): Email subject.
        html (bool): When True, send query as HTML. Defaults to False.

    Environment Variables:
        SENDGRID_API_KEY: SendGrid API key.
        SENDGRID_FROM_EMAIL: Verified SendGrid sender email address.

    Returns:
        Dict[str, Any]: Structured result with success status.
    """

    if not query or not query.strip():
        return {
            "success": False,
            "error": "Email body cannot be empty.",
        }

    to_email = kwargs.get("to_email")
    subject = kwargs.get("subject")
    html = kwargs.get("html", False)

    if not to_email or not str(to_email).strip():
        return {
            "success": False,
            "error": "to_email is required.",
        }

    if not subject or not str(subject).strip():
        return {
            "success": False,
            "error": "subject is required.",
        }

    if not isinstance(html, bool):
        return {
            "success": False,
            "error": "html must be a boolean value.",
        }

    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("SENDGRID_FROM_EMAIL")

    if not api_key:
        return {
            "success": False,
            "error": "SENDGRID_API_KEY environment variable is not set.",
        }

    if not from_email:
        return {
            "success": False,
            "error": "SENDGRID_FROM_EMAIL environment variable is not set.",
        }

    content_type = "text/html" if html else "text/plain"

    payload = {
        "personalizations": [
            {
                "to": [
                    {
                        "email": str(to_email).strip(),
                    }
                ]
            }
        ],
        "from": {
            "email": from_email.strip(),
        },
        "subject": str(subject).strip(),
        "content": [
            {
                "type": content_type,
                "value": query.strip(),
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            SENDGRID_MAIL_URL,
            json=payload,
            headers=headers,
            timeout=15,
        )

        if response.status_code == 202:
            return {
                "success": True,
                "status": response.status_code,
                "message": "Email accepted by SendGrid.",
            }

        if response.status_code in (401, 403):
            return {
                "success": False,
                "status": response.status_code,
                "error": (
                    "SendGrid authentication failed or the API key "
                    "does not have permission to send email."
                ),
            }

        if response.status_code == 429:
            return {
                "success": False,
                "status": response.status_code,
                "error": "SendGrid rate limit exceeded.",
            }

        try:
            error_data = response.json()
            errors = error_data.get("errors", [])

            if errors:
                error_message = "; ".join(
                    str(error.get("message", "Unknown SendGrid error"))
                    for error in errors
                )
            else:
                error_message = "SendGrid returned an unsuccessful response."

        except ValueError:
            error_message = (
                f"SendGrid request failed with HTTP "
                f"{response.status_code}."
            )

        return {
            "success": False,
            "status": response.status_code,
            "error": error_message,
        }

    except requests.RequestException as exc:
        return {
            "success": False,
            "error": f"SendGrid API request failed: {exc}",
        }