# RSS & Atom Feed Reader Tool

A fast, zero-dependency Python tool for parsing RSS 2.0 and Atom syndication feeds into clean structured JSON dictionaries.

## Features

- **Multi-Format Support**: Automatically detects and parses RSS 2.0 (`<rss><channel><item>`) and Atom (`<feed><entry>`) feeds.
- **Zero Dependencies**: Pure Python 3 standard library (`urllib.request` and `xml.etree.ElementTree`).
- **Resilient Parsing**: Gracefully handles missing tags, XML encoding variations, and network timeouts.
- **Configurable Item Limits**: Extract the latest `N` articles (default: `5`).

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `feed_url` | `string` | **Yes** | — | Web URL of the RSS 2.0 or Atom feed |
| `limit` | `integer` | No | `5` | Maximum number of articles to return |
| `timeout_seconds` | `integer` | No | `10` | HTTP request timeout in seconds |

## Example Usage

### Request
```json
{
  "feed_url": "https://news.ycombinator.com/rss",
  "limit": 3
}
```

### Response
```json
{
  "status": "success",
  "format": "rss2.0",
  "feed_url": "https://news.ycombinator.com/rss",
  "title": "Hacker News",
  "description": "Links for the intellectually curious, ranked by user votes.",
  "item_count": 3,
  "items": [
    {
      "title": "Example Post Title",
      "link": "https://news.ycombinator.com/item?id=12345",
      "summary": "Short article description excerpt...",
      "published": "Wed, 19 Aug 2026 10:00:00 GMT",
      "author": "author_user"
    }
  ]
}
```
