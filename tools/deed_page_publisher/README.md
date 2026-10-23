# deed.page Publisher Tool

A Python tool that publishes an HTML page to a live HTTPS URL at `https://<slug>.deed.page/` with one HTTP PUT to the [deed.page](https://deed.page/) REST API. Useful when an agent has generated a report, dashboard or landing page and needs to hand back a link.

## Prerequisites

None for a first publish: the deed.page free plan needs no account or API key, and the tool uses only the Python standard library.

The first publish of a slug returns a `token`. Keep it to update that slug later, either:

- Set it as the `DEED_PAGE_TOKEN` environment variable, or
- Pass it as the `token` parameter.

Free plan limits (see [deed.page/pricing](https://deed.page/pricing)): 25 sites, 25 MB per site, and 4 MB per request. This tool sends a single HTML document, so it stays within the 4 MB request cap.

## Parameters

| Parameter | Type | Required | Description | Default |
| :--- | :--- | :--- | :--- | :--- |
| `html` | `string` | Yes | Full HTML document, served as `index.html` | — |
| `slug` | `string` | Yes | Subdomain: lowercase letters, digits and hyphens | — |
| `token` | `string` | No | Token from the first publish of this slug; falls back to `DEED_PAGE_TOKEN` | — |

## Usage

```python
from tool import run_tool

page = "<!doctype html><title>Report</title><h1>Weekly report</h1>"

# First publish: returns the live URL and a token for this slug
first = run_tool(html=page, slug="weekly-report-7f3a")
print(first["url"])    # https://weekly-report-7f3a.deed.page/
token = first["token"]

# Update the same slug later
updated = run_tool(html=page.replace("Weekly", "Updated weekly"), slug="weekly-report-7f3a", token=token)
print(updated["version"])  # v2
```

Publishing to a slug someone else already owns returns `{"success": false, "status": 409, ...}`.

### CLI test

```bash
python tool.py   # publishes a demo page to a random slug and prints the JSON result
```

## Docs

- REST and MCP reference: [deed.page/docs](https://deed.page/docs)
- Remote MCP server (for MCP clients that prefer it over this tool): `https://deed.page/mcp`
- Agent skill: [f-o-x11/deed-page-skill](https://github.com/f-o-x11/deed-page-skill)
