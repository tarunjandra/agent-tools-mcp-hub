#!/usr/bin/env python3
import json
from typing import Any, Dict

def convert_format(content: str, target_format: str = "yaml", indent: int = 2) -> Dict[str, Any]:
    target = target_format.lower().strip()
    if not content:
        return {"status": "error", "error": "Content string cannot be empty"}
        
    try:
        # First attempt JSON parse
        parsed_data = json.loads(content)
    except json.JSONDecodeError:
        # Fallback simple line-based YAML-like or error
        return {"status": "error", "error": "Invalid input JSON/YAML format"}

    if target == "json":
        result = json.dumps(parsed_data, indent=indent, ensure_ascii=False)
        return {"status": "success", "target_format": "json", "result": result}
    elif target in ("yaml", "yml"):
        # Built-in lightweight YAML generator for zero external dependency compliance
        lines = []
        def _dump_yaml(val, current_indent=0):
            prefix = " " * current_indent
            if isinstance(val, dict):
                for k, v in val.items():
                    if isinstance(v, (dict, list)):
                        lines.append(f"{prefix}{k}:")
                        _dump_yaml(v, current_indent + indent)
                    else:
                        lines.append(f"{prefix}{k}: {v}")
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, (dict, list)):
                        lines.append(f"{prefix}-")
                        _dump_yaml(item, current_indent + indent)
                    else:
                        lines.append(f"{prefix}- {item}")
            else:
                lines.append(f"{prefix}{val}")
                
        _dump_yaml(parsed_data, 0)
        return {"status": "success", "target_format": "yaml", "result": "\n".join(lines)}
    else:
        return {"status": "error", "error": f"Unsupported target_format: {target_format}"}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    content = params.get("content", "")
    target_format = params.get("target_format", "yaml")
    indent = int(params.get("indent", 2))
    return convert_format(content, target_format, indent)
