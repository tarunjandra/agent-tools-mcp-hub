# ChromaDB Vector Store Query Tool

Run semantic-similarity (nearest-neighbour) searches against a local, on-disk [Chroma](https://www.trychroma.com/) vector database. Designed for RAG and retrieval agents that need to pull the most relevant stored chunks for a query.

## Features

- **Two query modes**: search by a **raw embedding vector** (`query_embedding` — no embedding model needed) or by **natural-language text** (`query_text` — embedded on the fly by the collection's embedding function).
- **Filtering**: narrow results with a metadata filter (`where`) and/or a document-content filter (`where_document`).
- **Structured output**: returns each match as `{ id, document, metadata, distance }`, plus `match_count` and `execution_time_ms` telemetry.
- **Graceful errors**: clear messages for a missing `chromadb` install, an unreachable database path, a non-existent collection, an embedding-dimension mismatch, or missing query input — never an unhandled exception.

## Setup

```bash
pip install -r requirements.txt
```

This tool reads an **existing** local Chroma database created with `chromadb.PersistentClient(path=...)`. No credentials or environment variables are required.

## Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `persist_directory` | `string` | **Yes** | — | Path to the on-disk Chroma database directory |
| `collection_name` | `string` | **Yes** | — | Name of the collection to query |
| `query_embedding` | `array<number>` | One of `query_embedding`/`query_text` | — | Raw query vector. Takes precedence over `query_text`; needs no embedding model |
| `query_text` | `string` | One of `query_embedding`/`query_text` | — | Natural-language query (requires the collection to have an embedding function) |
| `n_results` | `integer` | No | `5` | Maximum number of matches to return |
| `where` | `object` | No | — | Metadata filter, e.g. `{"source": "docs"}` |
| `where_document` | `object` | No | — | Document-content filter, e.g. `{"$contains": "gpu"}` |

## Usage Example

### Query by raw embedding vector
```python
from tool import run

response = run({
    "persist_directory": "./chroma_db",
    "collection_name": "knowledge_base",
    "query_embedding": [0.12, -0.03, 0.88, ...],
    "n_results": 3,
})
print(response)
```

### Query by text with a metadata filter
```python
from tool import run

response = run({
    "persist_directory": "./chroma_db",
    "collection_name": "knowledge_base",
    "query_text": "how do I configure GPU acceleration?",
    "n_results": 5,
    "where": {"source": "docs"},
})
print(response)
```

### Response Format
```json
{
  "status": "success",
  "collection": "knowledge_base",
  "query_type": "embedding",
  "matches": [
    {
      "id": "chunk-42",
      "document": "GPU acceleration is enabled by setting ...",
      "metadata": { "source": "docs", "page": 7 },
      "distance": 0.1834
    }
  ],
  "match_count": 1,
  "execution_time_ms": 3.21
}
```

### Error Response
```json
{
  "status": "error",
  "error": "Collection 'knowledge_base' not found in './chroma_db': ...",
  "matches": [],
  "match_count": 0,
  "execution_time_ms": 0.0
}
```

## Running the Self-Test

`tool.py` includes an offline self-test that builds a tiny temporary Chroma database (using explicit embeddings, so **no model download is required**), runs vector and metadata-filtered queries, and checks the error paths:

```bash
python tool.py
```
