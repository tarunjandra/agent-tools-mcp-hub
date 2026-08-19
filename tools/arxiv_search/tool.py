"""
ArXiv Research Paper Search Tool for AI Agents
"""
import json
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"
USER_AGENT = "AgentToolsHub/1.0 (https://github.com/tarunjandra/agent-tools-mcp-hub)"
ARXIV_API_URL = "https://export.arxiv.org/api/query"


def _text(element: Optional[ET.Element]) -> str:
    if element is None or element.text is None:
        return ""
    return " ".join(element.text.split())


def _pdf_url(entry: ET.Element, arxiv_id: str) -> str:
    for link in entry.findall(f"{ATOM_NS}link"):
        title = (link.get("title") or "").lower()
        link_type = (link.get("type") or "").lower()
        href = link.get("href") or ""
        if title == "pdf" or link_type == "application/pdf":
            return href
    if arxiv_id:
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    return ""


def _arxiv_id_from_entry(entry: ET.Element) -> str:
    raw_id = _text(entry.find(f"{ATOM_NS}id"))
    if "/abs/" in raw_id:
        return raw_id.rsplit("/abs/", 1)[-1]
    return raw_id


def search_arxiv(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Searches arXiv by topic and returns title, authors, abstract, and PDF link.
    """
    if not query or not str(query).strip():
        return {"success": False, "error": "query parameter is required."}

    try:
        limit = int(max_results)
    except (TypeError, ValueError):
        return {"success": False, "error": "max_results must be an integer between 1 and 25."}

    if limit < 1 or limit > 25:
        return {"success": False, "error": "max_results must be an integer between 1 and 25."}

    topic = str(query).strip()
    params = urllib.parse.urlencode(
        {
            "search_query": f"all:{topic}",
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
    )
    url = f"{ARXIV_API_URL}?{params}"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/atom+xml",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            payload = response.read()

        root = ET.fromstring(payload)
        papers: List[Dict[str, Any]] = []

        for entry in root.findall(f"{ATOM_NS}entry"):
            arxiv_id = _arxiv_id_from_entry(entry)
            authors = [
                _text(author.find(f"{ATOM_NS}name"))
                for author in entry.findall(f"{ATOM_NS}author")
                if _text(author.find(f"{ATOM_NS}name"))
            ]
            category = entry.find(f"{ARXIV_NS}primary_category")
            papers.append(
                {
                    "id": arxiv_id,
                    "title": _text(entry.find(f"{ATOM_NS}title")),
                    "authors": authors,
                    "abstract": _text(entry.find(f"{ATOM_NS}summary")),
                    "published": _text(entry.find(f"{ATOM_NS}published")),
                    "pdf_url": _pdf_url(entry, arxiv_id),
                    "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else _text(entry.find(f"{ATOM_NS}id")),
                    "primary_category": category.get("term") if category is not None else "",
                }
            )

        return {
            "success": True,
            "query": topic,
            "count": len(papers),
            "papers": papers,
        }
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP Error {e.code}: {e.reason}"}
    except ET.ParseError as e:
        return {"success": False, "error": f"Failed to parse arXiv response: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Failed to search arXiv: {str(e)}"}


if __name__ == "__main__":
    result = search_arxiv("transformer language models", max_results=3)
    print(json.dumps(result, indent=2))
