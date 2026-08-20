#!/usr/bin/env python3
"""
RSS & Atom Feed Reader Tool for Agent Tools & MCP Hub.
Fetches and parses XML RSS 2.0 / Atom syndication feeds into clean structured JSON.
"""
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import time


def _clean_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return text.strip()


def parse_feed_xml(xml_content: str, limit: int = 5) -> Dict[str, Any]:
    """Parse RSS 2.0 or Atom XML content into a structured dictionary."""
    root = ET.fromstring(xml_content)
    tag = root.tag.lower()

    # Detect Atom feeds (e.g. {http://www.w3.org/2005/Atom}feed or <feed>)
    if "feed" in tag:
        ns = {"atom": "http://www.w3.org/2005/Atom"} if "{" in root.tag else {}
        title_elem = root.find("atom:title", ns) if ns else root.find("title")
        subtitle_elem = root.find("atom:subtitle", ns) if ns else root.find("subtitle")
        
        feed_title = _clean_text(title_elem.text if title_elem is not None else "")
        feed_desc = _clean_text(subtitle_elem.text if subtitle_elem is not None else "")

        entries = root.findall("atom:entry", ns) if ns else root.findall("entry")
        items: List[Dict[str, Any]] = []

        for entry in entries[:limit]:
            e_title = entry.find("atom:title", ns) if ns else entry.find("title")
            e_summary = entry.find("atom:summary", ns) if ns else entry.find("summary")
            if e_summary is None:
                e_summary = entry.find("atom:content", ns) if ns else entry.find("content")
            
            e_link_elem = entry.find("atom:link", ns) if ns else entry.find("link")
            e_link = ""
            if e_link_elem is not None:
                e_link = e_link_elem.attrib.get("href", "") or _clean_text(e_link_elem.text)

            e_pub = entry.find("atom:published", ns) if ns else entry.find("published")
            if e_pub is None:
                e_pub = entry.find("atom:updated", ns) if ns else entry.find("updated")

            e_author = entry.find("atom:author/atom:name", ns) if ns else entry.find("author/name")

            items.append({
                "title": _clean_text(e_title.text if e_title is not None else ""),
                "link": e_link,
                "summary": _clean_text(e_summary.text if e_summary is not None else "")[:500],
                "published": _clean_text(e_pub.text if e_pub is not None else ""),
                "author": _clean_text(e_author.text if e_author is not None else "")
            })

        return {
            "status": "success",
            "format": "atom",
            "title": feed_title,
            "description": feed_desc,
            "item_count": len(items),
            "items": items
        }

    # Otherwise parse as standard RSS 2.0
    channel = root.find("channel")
    if channel is None:
        channel = root

    ch_title = _clean_text(channel.findtext("title"))
    ch_desc = _clean_text(channel.findtext("description"))
    ch_link = _clean_text(channel.findtext("link"))

    raw_items = channel.findall("item")
    items = []

    for it in raw_items[:limit]:
        title = _clean_text(it.findtext("title"))
        link = _clean_text(it.findtext("link"))
        desc = _clean_text(it.findtext("description"))
        pub_date = _clean_text(it.findtext("pubDate"))
        author = _clean_text(it.findtext("author") or it.findtext("dc:creator"))

        items.append({
            "title": title,
            "link": link,
            "summary": desc[:500],
            "published": pub_date,
            "author": author
        })

    return {
        "status": "success",
        "format": "rss2.0",
        "title": ch_title,
        "description": ch_desc,
        "link": ch_link,
        "item_count": len(items),
        "items": items
    }


def fetch_and_parse_feed(feed_url: str, limit: int = 5, timeout: int = 10) -> Dict[str, Any]:
    """Fetch an RSS / Atom feed from URL and parse its entries."""
    if not feed_url or not (feed_url.startswith("http://") or feed_url.startswith("https://")):
        return {
            "status": "error",
            "error": "Invalid URL. feed_url must start with http:// or https://",
            "items": [],
            "item_count": 0
        }

    req = urllib.request.Request(
        feed_url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AgentTools-MCP-Hub/1.0; +https://github.com/tarunjandra/agent-tools-mcp-hub)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_bytes = resp.read()
            xml_str = raw_bytes.decode("utf-8", errors="replace")
            result = parse_feed_xml(xml_str, limit=limit)
            result["feed_url"] = feed_url
            return result
    except urllib.error.HTTPError as e:
        return {
            "status": "error",
            "error": f"HTTP error {e.code}: {e.reason}",
            "feed_url": feed_url,
            "items": [],
            "item_count": 0
        }
    except urllib.error.URLError as e:
        return {
            "status": "error",
            "error": f"Network error: {str(e.reason)}",
            "feed_url": feed_url,
            "items": [],
            "item_count": 0
        }
    except ET.ParseError as e:
        return {
            "status": "error",
            "error": f"XML parse error: {str(e)}",
            "feed_url": feed_url,
            "items": [],
            "item_count": 0
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "feed_url": feed_url,
            "items": [],
            "item_count": 0
        }


def run(params: Dict[str, Any]) -> Dict[str, Any]:
    """Standard tool entrypoint."""
    feed_url = params.get("feed_url", "")
    limit = int(params.get("limit", 5))
    timeout = int(params.get("timeout_seconds", 10))
    return fetch_and_parse_feed(feed_url=feed_url, limit=limit, timeout=timeout)


if __name__ == "__main__":
    # Self-test using sample RSS 2.0 XML string
    sample_rss = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Tech News Feed</title>
        <link>https://example.com</link>
        <description>Daily technology updates</description>
        <item>
          <title>AI Advances in 2026</title>
          <link>https://example.com/ai-2026</link>
          <description>Deep dive into modern multi-agent systems and MCP.</description>
          <pubDate>Wed, 19 Aug 2026 12:00:00 GMT</pubDate>
          <author>editor@example.com</author>
        </item>
      </channel>
    </rss>
    """
    res = parse_feed_xml(sample_rss)
    print("Parsed Sample:", res)
    assert res["status"] == "success"
    assert res["title"] == "Tech News Feed"
    assert res["item_count"] == 1
    assert res["items"][0]["title"] == "AI Advances in 2026"
    print("✅ Self-test passed successfully!")
