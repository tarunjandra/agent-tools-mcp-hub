# Airtable Record Appender

A Python tool that appends one or more records to an Airtable base through the [Airtable Web API](https://airtable.com/developers/web/api/introduction).

## Prerequisites

A personal access token with the `data.records:write` scope for the base you are writing to. Create one at [airtable.com/create/tokens](https://airtable.com/create/tokens), then either:

- Set it as the `AIRTABLE_API_KEY` environment variable, or
- Pass it as the `token` parameter.

The token is sent as `Authorization: Bearer <token>`.

## Parameters

| Parameter | Type | Required | Description | Default |
| :--- | :--- | :--- | :--- | :--- |
| `base_id` | `string` | Yes | Base id, e.g. `appXXXXXXXXXXXXXX` | — |
| `table` | `string` | Yes | Table name or table id, e.g. `Leads` | — |
| `records` | `array` | Yes | Records to append | — |
| `token` | `string` | No | Access token; falls back to `AIRTABLE_API_KEY` | — |
| `typecast` | `boolean` | No | Let Airtable coerce values into the field type | `False` |

Each entry in `records` is either a plain field mapping or the wrapped form the API itself uses — both work:

```python
{"Name": "Ada", "Email": "ada@example.com"}   # plain
{"fields": {"Name": "Ada"}}                    # wrapped
```

## Usage

```python
import os
from tool import run_tool

os.environ["AIRTABLE_API_KEY"] = "patXXXXXXXXXXXXXX"

result = run_tool(
    base_id="appXXXXXXXXXXXXXX",
    table="Leads",
    records=[
        {"Name": "Ada Lovelace", "Email": "ada@example.com", "Source": "conference"},
        {"Name": "Grace Hopper", "Email": "grace@example.com"},
    ],
)

if result["success"]:
    print(f"appended {result['created_count']} record(s)")
    for record in result["created"]:
        print(record["id"], record["fields"])
else:
    print(result["error"])
```

### CLI test

```bash
AIRTABLE_API_KEY=patXXXXXXXXXXXXXX python tool.py
```

## Notes

- **Batches are split for you.** Airtable rejects more than **10** records in a single request, so a longer list is sent as several requests and the created ids are concatenated. `created_count` is the total across all of them.
- **A mid-batch failure returns what already landed.** If the third batch fails, the response carries `created` with everything written so far alongside the error, so a retry cannot silently duplicate the earlier rows.
- **Field names must match the base.** Airtable matches on the exact column name; a typo comes back as its own message rather than a generic failure. `typecast` is off by default so a type mismatch is reported instead of quietly rewritten.
- The table accepts either its name (`Leads`) or its id (`tblXXXXXXXXXXXXXX`); both characters that matter are URL-encoded before the request.
