"""Text diff analyzer tool for agent workspaces."""
import difflib
from typing import Dict, Any, List

def compute_text_diff(text_a: str, text_b: str, context_lines: int = 3) -> Dict[str, Any]:
    """
    Computes unified diff and summary metrics between two text payloads.
    """
    lines_a = text_a.splitlines(keepends=True)
    lines_b = text_b.splitlines(keepends=True)

    diff_generator = difflib.unified_diff(
        lines_a,
        lines_b,
        fromfile="original",
        tofile="modified",
        n=context_lines
    )
    diff_lines = list(diff_generator)

    additions = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))

    return {
        "unified_diff": "".join(diff_lines),
        "additions": additions,
        "deletions": deletions,
        "has_changes": len(diff_lines) > 0
    }
