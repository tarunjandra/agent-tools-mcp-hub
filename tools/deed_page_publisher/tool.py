"""
deed.page Publisher Tool for AI Agents

Publishes an HTML string to a live HTTPS URL at https://<slug>.deed.page/
with one HTTP PUT to the deed.page REST API. The free plan needs no account
or API key: the first publish of a slug returns a token, and sending that
token back (DEED_PAGE_TOKEN or the `token` argument) updates the same slug.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

API_URL = "https://deed.page/v1/sites"
SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
MAX_BODY_BYTES = 4 * 1024 * 1024  # single-request cap on deed.page


def publish_site(html: str, slug: str, token: Optional[str] = None, client: str = "agent-tools-mcp-hub", **kwargs: Any) -> Dict[str, Any]:
    """
    Publish (or update) a single-page site on deed.page.

    Args:
        html (str): Full HTML document to serve as index.html.
        slug (str): Subdomain to publish to (lowercase letters, digits, hyphens).
        token (str, optional): Token from an earlier publish of this slug, needed to update it.
            Falls back to the DEED_PAGE_TOKEN environment variable.
        client (str): Name sent in the X-Client header so the request is attributable.

    Returns:
        Dict[str, Any]: {"success": True, "url": ..., "slug": ..., "version": ..., "token": ...}
        or {"success": False, "error": ...}.
    """
    if not html or not html.strip():
        return {"success": False, "error": "html cannot be empty."}
    slug = (slug or "").strip().lower()
    if not SLUG_PATTERN.match(slug):
        return {"success": False, "error": "slug must be 1-63 lowercase letters, digits or hyphens, not starting or ending with a hyphen."}

    body = html.encode("utf-8")
    if len(body) > MAX_BODY_BYTES:
        return {"success": False, "error": "html is larger than the 4 MB single-request limit."}

    headers = {
        "Content-Type": "text/html; charset=utf-8",
        "X-Client": client,
        "User-Agent": "agent-tools-mcp-hub/deed_page_publisher",
    }
    token = token or os.environ.get("DEED_PAGE_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{API_URL}?{urllib.parse.urlencode({'slug': slug})}"
    req = urllib.request.Request(url, data=body, headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        return {"success": False, "status": e.code, "error": f"deed.page returned HTTP {e.code}: {detail}"}
    except Exception as e:  # network errors, timeouts, bad JSON
        return {"success": False, "error": f"Failed to publish: {str(e)}"}

    if not data.get("ok"):
        return {"success": False, "error": f"Unexpected response: {data}"}

    result = {
        "success": True,
        "url": data.get("url"),
        "slug": data.get("slug"),
        "version": data.get("version"),
    }
    # The token is only returned on the first publish of a slug; keep it to update later.
    if data.get("token"):
        result["token"] = data["token"]
    return result


def run_tool(html: str, slug: str, token: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
    """Entry point matching the hub's tool convention."""
    return publish_site(html=html, slug=slug, token=token, **kwargs)


if __name__ == "__main__":
    import secrets

    demo_slug = f"agent-tools-hub-demo-{secrets.token_hex(3)}"
    demo_html = "<!doctype html><title>Hello</title><h1>Published by an agent tool</h1>"
    print(json.dumps(run_tool(demo_html, demo_slug), indent=2))
