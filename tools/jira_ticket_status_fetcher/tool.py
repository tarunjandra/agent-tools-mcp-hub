"""
Jira Ticket Status Fetcher

Fetches a Jira Cloud issue's status, summary, and description
using the Jira REST API v3.
"""

import os
from typing import Any, Dict

import requests


def _extract_adf_text(node: Any) -> str:
    """
    Convert a Jira Atlassian Document Format (ADF) description
    into readable plain text.
    """
    if node is None:
        return ""

    if isinstance(node, str):
        return node

    if isinstance(node, list):
        parts = [_extract_adf_text(item) for item in node]
        return "\n".join(part for part in parts if part)

    if isinstance(node, dict):
        if node.get("type") == "text":
            return str(node.get("text", ""))

        content = node.get("content", [])
        if isinstance(content, list):
            parts = [_extract_adf_text(item) for item in content]
            text = " ".join(part for part in parts if part)

            if node.get("type") in {
                "paragraph",
                "heading",
                "listItem",
                "bulletList",
                "orderedList",
            }:
                return text.strip()

            return text

    return ""


def run_tool(query: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Fetch a Jira issue by issue key.

    Args:
        query: Jira issue key, for example "PROJ-123".

    Environment variables:
        JIRA_BASE_URL: Jira Cloud site URL,
                       e.g. https://example.atlassian.net
        JIRA_EMAIL: Atlassian account email
        JIRA_API_TOKEN: Atlassian API token

    Returns:
        Dictionary containing issue status, summary, and description.
    """

    if not query or not query.strip():
        return {
            "success": False,
            "error": "Jira issue key is required.",
        }

    issue_key = query.strip()

    jira_base_url = os.getenv("JIRA_BASE_URL")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_api_token = os.getenv("JIRA_API_TOKEN")

    if not jira_base_url:
        return {
            "success": False,
            "error": "JIRA_BASE_URL environment variable is not set.",
        }

    if not jira_email:
        return {
            "success": False,
            "error": "JIRA_EMAIL environment variable is not set.",
        }

    if not jira_api_token:
        return {
            "success": False,
            "error": "JIRA_API_TOKEN environment variable is not set.",
        }

    url = (
        f"{jira_base_url.rstrip('/')}"
        f"/rest/api/3/issue/{issue_key}"
    )

    try:
        response = requests.get(
            url,
            params={
                "fields": "summary,status,description",
            },
            auth=(jira_email, jira_api_token),
            headers={
                "Accept": "application/json",
            },
            timeout=15,
        )

        if response.status_code == 404:
            return {
                "success": False,
                "error": f"Jira issue '{issue_key}' was not found.",
            }

        if response.status_code in (401, 403):
            return {
                "success": False,
                "error": (
                    "Jira authentication failed or the account does "
                    "not have permission to view this issue."
                ),
            }

        response.raise_for_status()

        data = response.json()
        fields = data.get("fields", {})

        status = fields.get("status") or {}
        description = _extract_adf_text(
            fields.get("description")
        ).strip()

        return {
            "success": True,
            "data": {
                "key": data.get("key", issue_key),
                "summary": fields.get("summary"),
                "status": status.get("name"),
                "description": description or None,
            },
        }

    except requests.RequestException as exc:
        return {
            "success": False,
            "error": f"Jira API request failed: {exc}",
        }

    except ValueError:
        return {
            "success": False,
            "error": "Jira returned an invalid JSON response.",
        }