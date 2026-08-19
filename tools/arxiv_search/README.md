# ArXiv Research Paper Search Tool

A zero-auth search tool that queries the public arXiv API and returns paper titles, authors, abstracts, and PDF links.

## Parameters

| Parameter | Type | Required | Description | Default |
| :--- | :--- | :--- | :--- | :--- |
| `query` | `string` | Yes | Research topic or search query | - |
| `max_results` | `integer` | No | Maximum number of papers to return (1-25) | `5` |

## Usage

```python
from tool import search_arxiv

result = search_arxiv(query="graph neural networks", max_results=3)
if result["success"]:
    for paper in result["papers"]:
        print(f"{paper['title']} ({paper['id']})")
        print(paper["pdf_url"])
```
