# CrewAI Wrapper Demo

Connect any tool in this hub to a [CrewAI](https://docs.crewai.com) agent — without writing a wrapper class per tool.

Every tool here shares one contract:

- a `run_tool(**kwargs)` function returning `{"success": bool, "data" | "error"}`
- a `metadata.json` whose `parameters` block is already **JSON Schema**

CrewAI's `BaseTool` wants a Pydantic `args_schema`. Those two facts are enough to generate the adapter, so **one adapter covers every conforming tool** instead of a hand-written class per tool.

Measured against this repo: **17 of 40 tools wrap automatically today.** The rest are reported as skips, never fatal — see [Coverage](#coverage).

## Parameters

`run_tool()` inspects a hub tool and reports the CrewAI tool it would produce. It does not require CrewAI to be installed.

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `tool_name` | `string` | Yes | Folder name of the hub tool to inspect, e.g. `jwt_decoder` |
| `tools_dir` | `string` | No | Path to the hub's tools directory (default `tools`) |

## Installation

```bash
pip install -r requirements.txt
```

> **CrewAI requires Python 3.10–3.13.** As of `crewai` 1.15 the package declares `requires-python = ">=3.10,<3.14"`. On Python 3.14 pip silently resolves to `crewai` 0.11.2 from early 2024, where `from crewai.tools import BaseTool` does not exist. If the imports below fail, check your interpreter version first.

`crewai` is imported lazily, inside the functions that need it, so `run_tool()` and `python scripts/validate_tools.py` both work without CrewAI installed.

---

## Step 1 — Inspect a tool

Before wrapping anything, see what adapter a hub tool will produce:

```python
from tool import run_tool

print(run_tool(tool_name="jwt_decoder"))
```

```json
{
  "success": true,
  "data": {
    "hub_tool": "jwt_decoder",
    "crewai_tool_name": "JWT / Base64 Token Decoder",
    "crewai_description": "Decodes JSON Web Tokens (JWT) and Base64Url strings to inspect header, payload claims, and expiration status without requiring private keys.",
    "args_schema_class": "JwtDecoderInput",
    "argument_count": 1,
    "required_count": 1,
    "arguments": [
      {
        "name": "token",
        "json_type": "string",
        "python_type": "str",
        "required": true,
        "default": null,
        "description": "The JWT token string or base64url encoded string to decode"
      }
    ],
    "importable": true,
    "import_note": null
  }
}
```

## Step 2 — Wrap a single tool

```python
from tool import make_crewai_tool

jwt_tool = make_crewai_tool("jwt_decoder")

print(jwt_tool.name)                            # JWT / Base64 Token Decoder
print(jwt_tool.args_schema.model_json_schema()) # generated from metadata.json
```

`name` and `description` come straight from `metadata.json`, so the text the agent reasons over is the same text that documents the tool.

## Step 3 — Wrap the entire catalogue

```python
from tool import load_all_crewai_tools

tools, skipped = load_all_crewai_tools()

print(f"wrapped {len(tools)} tools")
for reason in skipped:
    print("skipped:", reason)
```

```
wrapped 17 tools
skipped: discord_webhook_announcer_ts: has no tool.py (likely a TypeScript or Go tool) -- skipped.
skipped: arxiv_search: 'arxiv_search' defines no callable run_tool().
skipped: pdf_text_extractor: Importing 'pdf_text_extractor' failed: ModuleNotFoundError: No module named 'pypdf'
...
```

Tools that cannot be wrapped are reported, never fatal.

### Coverage

Run against this repo's 40 tool folders, `load_all_crewai_tools()` wraps 17 and skips 23:

| Outcome | Count | Cause |
| :--- | ---: | :--- |
| Wrapped | 17 | Python tool exposing `run_tool()` |
| Skipped | 8 | No `tool.py` — TypeScript tools |
| Skipped | 10 | Python, but exposes a differently-named entry point (`get_weather`, `search_wikipedia`, `search_arxiv`, …) rather than `run_tool()` |
| Skipped | 5 | Third-party dependency not installed (`pypdf`, `psycopg2`, `qrcode`, `redis`, `yfinance`) |

The last group wraps fine once you `pip install -r` that tool's requirements — those five are an environment gap, not a code one. The middle group would need either a `run_tool()` alias in those tools or an adapter that falls back to the module's single public callable.

## Step 4 — Build an Agent, Task and Crew

A complete, runnable example using a real hub tool:

```python
import os
from crewai import Agent, Crew, Task
from tool import make_crewai_tool

# A throwaway unsigned token: {"iss":"demo","sub":"user-42","exp":1700000000}
SAMPLE_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJkZW1vIiwic3ViIjoidXNlci00MiIsImV4cCI6MTcwMDAwMDAwMH0"
    ".not-a-real-signature"
)

jwt_tool = make_crewai_tool("jwt_decoder")

analyst = Agent(
    role="Security Analyst",
    goal="Inspect authentication tokens and report what they contain.",
    backstory=(
        "You review tokens from client applications and explain, in plain "
        "language, who issued them and whether they are still valid."
    ),
    tools=[jwt_tool],
    verbose=True,
)

task = Task(
    description=f"Decode this JWT and summarise it: {SAMPLE_TOKEN}",
    expected_output="A short summary of the token's issuer, subject and expiry status.",
    agent=analyst,
)

crew = Crew(agents=[analyst], tasks=[task], verbose=True)

if os.getenv("OPENAI_API_KEY"):
    print(crew.kickoff())
```

### Call the tool directly first

`crew.kickoff()` needs an LLM provider key. The tool itself does not — invoke it directly before involving an agent:

```python
print(jwt_tool.run(token=SAMPLE_TOKEN))
```

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "iss": "demo",
    "sub": "user-42",
    "exp": 1700000000
  },
  "signature_present": true,
  "is_expired": true,
  "expires_in_seconds": -87393793
}
```

Do this before wiring up a crew. It separates *"my tool is broken"* from *"the agent chose not to call my tool"* — two failures that look identical once an LLM is in the loop.

---

## Gotchas

- **Errors are returned, not raised.** Hub tools return `{"success": false, "error": "..."}`. The adapter converts that into text and hands it back, so the agent can read the message and correct itself instead of an exception killing the crew.

  ```python
  print(jwt_tool.run(token="not-a-jwt"))
  # Tool 'jwt_decoder' failed: Invalid JWT format. Expected exactly 3
  # period-separated segments (header.payload.signature).
  ```

- **TypeScript tools are skipped, not fatal.** Eight tools in this hub are `.ts` and have no `tool.py`. `load_all_crewai_tools()` reports them in `skipped` and carries on.

- **The `run_tool()` contract is not universal.** Ten Python tools here expose a differently-named function instead — `open_meteo_weather` has `get_weather()`, `wikipedia_search` has `search_wikipedia()`. They are skipped with a clear reason rather than silently mis-wrapped. Adding a `run_tool()` alias to those tools would bring them in with no change to this adapter.

- **Descriptions are prompt text.** CrewAI shows `description` and each field's description to the LLM. They come from `metadata.json`, so vague wording there becomes a vague prompt — a common reason an agent calls a tool with the wrong argument.

- **Optional arguments are stripped when unset.** Fields that come through as `None` are removed before calling the hub tool, so the tool applies its own documented defaults rather than receiving an explicit `None`.

- **Tools needing credentials still need them.** Wrapping does not supply configuration; tools read their own environment variables. See each tool's `README.md`.

- **The generated class name** is the tool folder in CamelCase plus `Input` — `jwt_decoder` becomes `JwtDecoderInput`.
