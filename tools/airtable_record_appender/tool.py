"""
Airtable Record Appender

Appends records to an Airtable base through the Airtable Web API.

Requires a personal access token with the `data.records:write` scope for the
base you are writing to: https://airtable.com/create/tokens
The token can be passed via the `token` parameter or the
AIRTABLE_API_KEY environment variable.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

API_URL = "https://api.airtable.com/v0"

# The API rejects more than 10 records in one request, so larger batches are
# split and sent one request at a time.
MAX_RECORDS_PER_REQUEST = 10


def _post_records(base_id: str, table: str, records: List[Dict[str, Any]],
                  token: str, typecast: bool, timeout: int = 20) -> Dict[str, Any]:
    """Send one batch of at most MAX_RECORDS_PER_REQUEST records."""
    url = "%s/%s/%s" % (
        API_URL,
        urllib.parse.quote(base_id, safe=""),
        urllib.parse.quote(table, safe=""),
    )
    payload: Dict[str, Any] = {"records": records}
    if typecast:
        payload["typecast"] = True

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (AgentToolsHub/1.0)",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def run_tool(
    base_id: str,
    table: str,
    records: List[Dict[str, Any]],
    token: Optional[str] = None,
    typecast: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Append records to an Airtable table.

    Args:
        base_id: Base identifier, e.g. "appXXXXXXXXXXXXXX".
        table: Table name or id, e.g. "Leads".
        records: Records to append, each one either a plain fields mapping
            (``{"Name": "Ada"}``) or a wrapped one (``{"fields": {...}}``).
        token: Airtable personal access token; falls back to the
            AIRTABLE_API_KEY environment variable.
        typecast: Let Airtable convert values that do not match the field type
            (a string into a number field, say). Off by default so a mismatch is
            reported rather than quietly rewritten.

    Returns:
        Dict with the created record ids and any per-record errors.
    """
    key = (token or os.getenv("AIRTABLE_API_KEY") or "").strip()
    if not key:
        return {
            "success": False,
            "error": (
                "Airtable token is required. Pass token or set the "
                "AIRTABLE_API_KEY environment variable (https://airtable.com/create/tokens)."
            ),
        }

    if not isinstance(base_id, str) or not base_id.strip().startswith("app"):
        return {"success": False, "error": 'base_id must look like "appXXXXXXXXXXXXXX".'}

    if not isinstance(table, str) or not table.strip():
        return {"success": False, "error": "table must be a non-empty table name or id."}

    if not isinstance(records, list) or not records:
        return {"success": False, "error": "records must be a non-empty list of field mappings."}

    # Both shapes are accepted because both are what people write: the raw
    # fields mapping, or the {"fields": {...}} wrapper the API itself uses.
    normalised: List[Dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            return {"success": False, "error": "records[%d] must be an object." % index}
        fields = record.get("fields") if "fields" in record else record
        if not isinstance(fields, dict) or not fields:
            return {"success": False, "error": "records[%d] has no fields to write." % index}
        normalised.append({"fields": fields})

    created: List[Dict[str, Any]] = []
    try:
        for start in range(0, len(normalised), MAX_RECORDS_PER_REQUEST):
            batch = normalised[start:start + MAX_RECORDS_PER_REQUEST]
            response = _post_records(base_id.strip(), table.strip(), batch, key, typecast)
            for record in response.get("records", []):
                created.append({
                    "id": record.get("id"),
                    "created_time": record.get("createdTime"),
                    "fields": record.get("fields"),
                })
    except urllib.error.HTTPError as error:
        # Airtable explains itself in the body -- an unknown field name, a bad
        # token, a table that does not exist -- so that text is what gets back.
        detail = ""
        try:
            body = json.loads(error.read().decode("utf-8"))
            detail = body.get("error", {}).get("message") or body.get("error") or ""
        except Exception:
            detail = ""
        return {
            "success": False,
            "error": "Airtable returned HTTP %s%s" % (error.code, ": " + str(detail) if detail else ""),
            "created": created,
        }
    except Exception as error:  # noqa: BLE001
        return {"success": False, "error": str(error), "created": created}

    return {
        "success": True,
        "created_count": len(created),
        "created": created,
    }


if __name__ == "__main__":
    print(json.dumps(
        run_tool(
            base_id="appXXXXXXXXXXXXXX",
            table="Leads",
            records=[{"Name": "Ada Lovelace", "Email": "ada@example.com"}],
        ),
        indent=2,
    ))
