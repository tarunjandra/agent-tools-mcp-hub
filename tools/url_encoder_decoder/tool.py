#!/usr/bin/env python3
import urllib.parse
from typing import Any, Dict

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    text = params.get("text", "")
    action = params.get("action", "encode").lower().strip()
    if action == "decode":
        result = urllib.parse.unquote(text)
    else:
        result = urllib.parse.quote(text, safe="")
    return {"status": "success", "action": action, "result": result}
