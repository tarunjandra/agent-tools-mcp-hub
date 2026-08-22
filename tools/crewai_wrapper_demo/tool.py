"""
CrewAI Wrapper Demo

Adapts any tool in this hub into a CrewAI tool, automatically.

Every tool here shares one contract: a `run_tool(**kwargs)` function returning
{"success": bool, "data"|"error"}, plus a metadata.json whose "parameters" block
is already JSON Schema. CrewAI's BaseTool wants a Pydantic `args_schema`. Those
two facts are enough to generate the adapter, so a single wrapper covers the
whole catalogue instead of a hand-written class per tool.

`crewai` and `pydantic` are imported lazily inside the functions that need them,
so `run_tool()` and `scripts/validate_tools.py` work without CrewAI installed.
"""

import importlib.util
import json
import os
from typing import Any, Dict, List, Optional, Tuple

# JSON Schema types, as used by every metadata.json here, mapped to the Python
# types Pydantic builds an args_schema from.
_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _python_type(schema: Dict[str, Any]) -> Any:
    """Translates one JSON Schema property into a Python type."""
    return _TYPE_MAP.get(str(schema.get("type", "string")).lower(), Any)


def _read_metadata(tool_name: str, tools_dir: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Loads a hub tool's metadata.json. Returns (metadata, error)."""
    path = os.path.join(tools_dir, tool_name, "metadata.json")
    if not os.path.isfile(path):
        return None, f"No metadata.json found for tool '{tool_name}' at '{path}'."
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle), None
    except json.JSONDecodeError as exc:
        return None, f"metadata.json for '{tool_name}' is not valid JSON: {exc}"


def _import_run_tool(tool_name: str, tools_dir: str) -> Tuple[Optional[Any], Optional[str]]:
    """
    Imports a hub tool's `run_tool` by file path.

    Tools are standalone folders, not an installed package, so importlib is used
    directly. TypeScript tools have no tool.py and are reported as a skip rather
    than an error -- 8 of the tools in this hub are .ts.
    """
    path = os.path.join(tools_dir, tool_name, "tool.py")
    if not os.path.isfile(path):
        return None, f"'{tool_name}' has no tool.py (likely a TypeScript or Go tool) -- skipped."

    try:
        spec = importlib.util.spec_from_file_location(f"hub_tool_{tool_name}", path)
        if spec is None or spec.loader is None:
            return None, f"Could not build an import spec for '{tool_name}'."
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:
        # A missing third-party dependency is the usual cause; that is the
        # tool's problem, not the adapter's, so report and move on.
        return None, f"Importing '{tool_name}' failed: {type(exc).__name__}: {exc}"

    run = getattr(module, "run_tool", None)
    if not callable(run):
        return None, f"'{tool_name}' defines no callable run_tool()."
    return run, None


def _build_args_schema(tool_name: str, parameters: Dict[str, Any]) -> Any:
    """Generates a Pydantic model from a metadata.json 'parameters' schema."""
    from pydantic import Field, create_model

    properties = parameters.get("properties") or {}
    required = parameters.get("required") or []
    if not isinstance(required, list):
        required = []

    fields: Dict[str, Any] = {}
    for name, schema in properties.items():
        if not isinstance(schema, dict):
            continue
        annotation = _python_type(schema)
        description = str(schema.get("description", ""))

        if name in required:
            # Ellipsis marks the field required, matching JSON Schema.
            fields[name] = (annotation, Field(..., description=description))
        else:
            fields[name] = (
                Optional[annotation],
                Field(default=schema.get("default"), description=description),
            )

    class_name = "".join(part.capitalize() for part in tool_name.split("_")) + "Input"
    return create_model(class_name, **fields)


def _format_result(tool_name: str, result: Any) -> str:
    """
    Converts a hub tool's {"success": ...} dict into the string CrewAI expects.

    Errors come back as text rather than raised, so the agent can read what went
    wrong and correct itself instead of the exception killing the crew.
    """
    if not isinstance(result, dict):
        return str(result)

    if not result.get("success"):
        return f"Tool '{tool_name}' failed: {result.get('error', 'unknown error')}"

    data = result.get("data", result)
    return json.dumps(data, indent=2, default=str)


def make_crewai_tool(tool_name: str, tools_dir: str = "tools") -> Any:
    """
    Builds a ready-to-use CrewAI BaseTool instance from a hub tool.

    Args:
        tool_name (str): Folder name under `tools_dir`, e.g. "jwt_decoder".
        tools_dir (str): Path to the hub's tools directory.

    Returns:
        A CrewAI BaseTool instance wrapping that tool.

    Raises:
        ValueError: if the tool's metadata or implementation cannot be loaded.
    """
    from crewai.tools import BaseTool

    metadata, error = _read_metadata(tool_name, tools_dir)
    if error:
        raise ValueError(error)

    run, error = _import_run_tool(tool_name, tools_dir)
    if error:
        raise ValueError(error)

    schema_model = _build_args_schema(tool_name, metadata.get("parameters") or {})

    # Captured for the closure below; CrewAI's BaseTool is a Pydantic model, so
    # `_run` reads these from the enclosing scope rather than from self.
    hub_run = run
    hub_name = tool_name

    class HubTool(BaseTool):
        name: str = metadata.get("display_name") or tool_name
        description: str = metadata.get("description") or f"Runs the '{tool_name}' tool."
        args_schema: type = schema_model

        def _run(self, **kwargs: Any) -> str:
            # Drop unset optionals so the hub tool applies its own defaults.
            cleaned = {k: v for k, v in kwargs.items() if v is not None}
            try:
                return _format_result(hub_name, hub_run(**cleaned))
            except Exception as exc:
                return f"Tool '{hub_name}' raised {type(exc).__name__}: {exc}"

    return HubTool()


def load_all_crewai_tools(tools_dir: str = "tools") -> Tuple[List[Any], List[str]]:
    """
    Wraps every hub tool that can be loaded.

    Returns:
        (tools, skipped): the CrewAI tool instances, and a readable reason for
        each tool that could not be wrapped (TypeScript tools, missing
        dependencies, malformed metadata).
    """
    tools: List[Any] = []
    skipped: List[str] = []

    if not os.path.isdir(tools_dir):
        return tools, [f"No tools directory at '{tools_dir}'."]

    for entry in sorted(os.listdir(tools_dir)):
        if entry.startswith((".", "_")):
            continue
        if not os.path.isdir(os.path.join(tools_dir, entry)):
            continue
        try:
            tools.append(make_crewai_tool(entry, tools_dir))
        except Exception as exc:
            skipped.append(f"{entry}: {exc}")

    return tools, skipped


def run_tool(tool_name: str = "", tools_dir: str = "tools", **kwargs: Any) -> Dict[str, Any]:
    """
    Reports the CrewAI tool that would be generated for a given hub tool.

    Inspects the named tool and describes the resulting CrewAI tool -- its name,
    description and generated argument schema -- without requiring CrewAI to be
    installed.

    Args:
        tool_name (str): Folder name under `tools_dir`, e.g. "jwt_decoder".
        tools_dir (str): Path to the hub's tools directory.

    Returns:
        Dict[str, Any]: {"success": True, "data": {...}} describing the adapter,
        or {"success": False, "error": "..."} with a readable explanation.
    """
    if not tool_name or not str(tool_name).strip():
        return {"success": False, "error": "Parameter 'tool_name' is required (e.g. 'jwt_decoder')."}

    tool_name = str(tool_name).strip()

    metadata, error = _read_metadata(tool_name, tools_dir)
    if error:
        return {"success": False, "error": error}

    _, import_error = _import_run_tool(tool_name, tools_dir)

    parameters = metadata.get("parameters") or {}
    properties = parameters.get("properties") or {}
    required = parameters.get("required") or []

    arguments = [
        {
            "name": name,
            "json_type": schema.get("type", "string"),
            "python_type": getattr(_python_type(schema), "__name__", "Any"),
            "required": name in required,
            "default": schema.get("default"),
            "description": schema.get("description", ""),
        }
        for name, schema in properties.items()
        if isinstance(schema, dict)
    ]

    return {
        "success": True,
        "data": {
            "hub_tool": tool_name,
            "crewai_tool_name": metadata.get("display_name") or tool_name,
            "crewai_description": metadata.get("description", ""),
            "args_schema_class": "".join(p.capitalize() for p in tool_name.split("_")) + "Input",
            "argument_count": len(arguments),
            "required_count": sum(1 for a in arguments if a["required"]),
            "arguments": arguments,
            "importable": import_error is None,
            "import_note": import_error,
        },
    }


if __name__ == "__main__":
    output = run_tool(tool_name="jwt_decoder", tools_dir="tools")
    print("Test execution output:", json.dumps(output, indent=2, default=str))
