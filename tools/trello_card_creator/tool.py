"""
Trello Card Creator

Creates a new task card in a specified Trello list using
the Trello REST API.
"""

import os
from typing import Any, Dict

import requests


TRELLO_CARDS_URL = "https://api.trello.com/1/cards"


def run_tool(query: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Create a Trello card.

    Args:
        query: Card title/name.
        list_id: Trello list ID where the card will be created.
        description: Optional card description.

    Environment Variables:
        TRELLO_API_KEY: Trello API key.
        TRELLO_TOKEN: Trello API token.

    Returns:
        Structured dictionary containing the created card details
        or an error.
    """

    if not query or not query.strip():
        return {
            "success": False,
            "error": "Card title is required.",
        }

    list_id = kwargs.get("list_id")
    description = kwargs.get("description", "")

    if not list_id or not str(list_id).strip():
        return {
            "success": False,
            "error": "list_id is required.",
        }

    api_key = os.getenv("TRELLO_API_KEY")
    token = os.getenv("TRELLO_TOKEN")

    if not api_key:
        return {
            "success": False,
            "error": "TRELLO_API_KEY environment variable is not set.",
        }

    if not token:
        return {
            "success": False,
            "error": "TRELLO_TOKEN environment variable is not set.",
        }

    params = {
        "key": api_key,
        "token": token,
    }

    payload = {
        "name": query.strip(),
        "idList": str(list_id).strip(),
        "desc": str(description).strip() if description else "",
    }

    try:
        response = requests.post(
            TRELLO_CARDS_URL,
            params=params,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=15,
        )

        if response.status_code in (401, 403):
            return {
                "success": False,
                "status": response.status_code,
                "error": (
                    "Trello authentication failed or the token "
                    "does not have permission to create cards."
                ),
            }

        if response.status_code == 404:
            return {
                "success": False,
                "status": response.status_code,
                "error": (
                    "The specified Trello list was not found "
                    "or is not accessible."
                ),
            }

        if response.status_code == 429:
            return {
                "success": False,
                "status": response.status_code,
                "error": "Trello API rate limit exceeded.",
            }

        if not response.ok:
            try:
                error_data = response.json()

                if isinstance(error_data, dict):
                    error_message = (
                        error_data.get("message")
                        or error_data.get("error")
                        or f"Trello API returned HTTP {response.status_code}."
                    )
                else:
                    error_message = (
                        f"Trello API returned HTTP {response.status_code}."
                    )

            except ValueError:
                error_message = (
                    response.text.strip()
                    or f"Trello API returned HTTP {response.status_code}."
                )

            return {
                "success": False,
                "status": response.status_code,
                "error": error_message,
            }

        data = response.json()

        return {
            "success": True,
            "status": response.status_code,
            "data": {
                "id": data.get("id"),
                "name": data.get("name"),
                "description": data.get("desc"),
                "list_id": data.get("idList"),
                "url": data.get("url"),
                "short_url": data.get("shortUrl"),
            },
        }

    except requests.Timeout:
        return {
            "success": False,
            "error": "Trello API request timed out.",
        }

    except requests.RequestException as exc:
        return {
            "success": False,
            "error": f"Trello API request failed: {exc}",
        }

    except ValueError:
        return {
            "success": False,
            "error": "Trello returned an invalid JSON response.",
        }