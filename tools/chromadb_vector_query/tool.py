#!/usr/bin/env python3
"""
ChromaDB Vector Store Query Tool for Agent Tools & MCP Hub.

Runs semantic-similarity (nearest-neighbour) searches against a local, on-disk
Chroma vector database. Supports querying either by a raw embedding vector
(no embedding model required) or by natural-language text (embedded on the fly
using the collection's configured embedding function).
"""
from typing import Any, Dict, List, Optional, Sequence, Union
import time


def _flatten_query_result(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert Chroma's per-query list-of-lists response into a flat list of match
    dicts for a single query. Chroma returns each field (ids, documents,
    metadatas, distances) as a list with one entry per submitted query; this
    tool submits exactly one query, so we read index 0 of each.
    """
    ids = (raw.get("ids") or [[]])[0]
    documents = (raw.get("documents") or [[]])[0] or [None] * len(ids)
    metadatas = (raw.get("metadatas") or [[]])[0] or [None] * len(ids)
    distances = (raw.get("distances") or [[]])[0] or [None] * len(ids)

    matches = []
    for i, _id in enumerate(ids):
        matches.append({
            "id": _id,
            "document": documents[i] if i < len(documents) else None,
            "metadata": metadatas[i] if i < len(metadatas) else None,
            "distance": distances[i] if i < len(distances) else None,
        })
    return matches


def query_chroma(
    persist_directory: str,
    collection_name: str,
    query_text: Optional[str] = None,
    query_embedding: Optional[Sequence[float]] = None,
    n_results: int = 5,
    where: Optional[Dict[str, Any]] = None,
    where_document: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Query a local Chroma collection for the nearest matches to a text or vector.

    Args:
        persist_directory: Path to the on-disk Chroma database directory.
        collection_name: Name of the collection to query.
        query_text: Natural-language query. Requires the collection to have an
            embedding function (Chroma's default downloads a model on first use).
        query_embedding: Raw query vector (list of floats). Takes precedence over
            query_text and needs no embedding model.
        n_results: Maximum number of matches to return.
        where: Optional metadata filter, e.g. {"source": "docs"}.
        where_document: Optional document-content filter, e.g. {"$contains": "gpu"}.

    Returns:
        Dict with status, collection, query_type, matches, match_count and
        execution_time_ms.
    """
    start_time = time.perf_counter()

    if query_embedding is None and not (query_text and query_text.strip()):
        return {
            "status": "error",
            "error": "Provide either 'query_text' (non-empty) or 'query_embedding'.",
            "matches": [],
            "match_count": 0,
            "execution_time_ms": 0.0,
        }

    if n_results is None or n_results < 1:
        return {
            "status": "error",
            "error": "'n_results' must be a positive integer.",
            "matches": [],
            "match_count": 0,
            "execution_time_ms": 0.0,
        }

    try:
        import chromadb
    except ImportError:
        return {
            "status": "error",
            "error": "The 'chromadb' package is not installed. Run: pip install -r requirements.txt",
            "matches": [],
            "match_count": 0,
            "execution_time_ms": 0.0,
        }

    try:
        client = chromadb.PersistentClient(path=persist_directory)
    except Exception as exc:  # noqa: BLE001 - surface any client init failure cleanly
        return {
            "status": "error",
            "error": f"Failed to open Chroma database at '{persist_directory}': {exc}",
            "matches": [],
            "match_count": 0,
            "execution_time_ms": 0.0,
        }

    try:
        collection = client.get_collection(name=collection_name)
    except Exception as exc:  # noqa: BLE001 - get_collection raises if it doesn't exist
        return {
            "status": "error",
            "error": f"Collection '{collection_name}' not found in '{persist_directory}': {exc}",
            "matches": [],
            "match_count": 0,
            "execution_time_ms": 0.0,
        }

    # Only request fields that are cheap and useful; ids are always returned.
    include = ["documents", "metadatas", "distances"]
    query_kwargs: Dict[str, Any] = {"n_results": int(n_results), "include": include}
    if where:
        query_kwargs["where"] = where
    if where_document:
        query_kwargs["where_document"] = where_document

    if query_embedding is not None:
        query_type = "embedding"
        query_kwargs["query_embeddings"] = [list(query_embedding)]
    else:
        query_type = "text"
        query_kwargs["query_texts"] = [query_text]

    try:
        raw = collection.query(**query_kwargs)
    except Exception as exc:  # noqa: BLE001 - dimension mismatch, missing embedder, etc.
        return {
            "status": "error",
            "error": f"Query failed: {exc}",
            "matches": [],
            "match_count": 0,
            "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 3),
        }

    matches = _flatten_query_result(raw)
    return {
        "status": "success",
        "collection": collection_name,
        "query_type": query_type,
        "matches": matches,
        "match_count": len(matches),
        "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 3),
    }


def run(params: Dict[str, Any]) -> Dict[str, Any]:
    """Standard entry point for MCP agent tools."""
    return query_chroma(
        persist_directory=params.get("persist_directory", ""),
        collection_name=params.get("collection_name", ""),
        query_text=params.get("query_text"),
        query_embedding=params.get("query_embedding"),
        n_results=params.get("n_results", 5),
        where=params.get("where"),
        where_document=params.get("where_document"),
    )


if __name__ == "__main__":
    # Offline self-test: build a tiny persistent Chroma DB using explicit
    # embeddings (so no embedding model needs to be downloaded), then query it.
    import os
    import shutil
    import tempfile

    try:
        import chromadb
    except ImportError:
        print("Skipping self-test: 'chromadb' is not installed.")
        raise SystemExit(0)

    tmp_dir = tempfile.mkdtemp(prefix="chroma_selftest_")
    try:
        client = chromadb.PersistentClient(path=tmp_dir)
        collection = client.create_collection(name="demo")
        # 3 orthogonal-ish vectors so nearest-neighbour is unambiguous.
        collection.add(
            ids=["a", "b", "c"],
            embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            documents=["about cats", "about dogs", "about cars"],
            metadatas=[{"topic": "pets"}, {"topic": "pets"}, {"topic": "vehicles"}],
        )

        # Query near the first vector -> expect doc "a" as the top match.
        res = run({
            "persist_directory": tmp_dir,
            "collection_name": "demo",
            "query_embedding": [0.9, 0.1, 0.0],
            "n_results": 2,
        })
        print("Vector query result:", res)
        assert res["status"] == "success", res
        assert res["match_count"] == 2, res
        assert res["matches"][0]["id"] == "a", res
        assert res["matches"][0]["document"] == "about cats", res

        # Metadata filter -> only the vehicles doc.
        res2 = run({
            "persist_directory": tmp_dir,
            "collection_name": "demo",
            "query_embedding": [0.0, 0.0, 1.0],
            "n_results": 5,
            "where": {"topic": "vehicles"},
        })
        assert res2["status"] == "success", res2
        assert res2["match_count"] == 1, res2
        assert res2["matches"][0]["id"] == "c", res2

        # Missing collection -> graceful error.
        res3 = run({
            "persist_directory": tmp_dir,
            "collection_name": "does_not_exist",
            "query_embedding": [1.0, 0.0, 0.0],
        })
        assert res3["status"] == "error", res3

        # No query input -> graceful error.
        res4 = run({"persist_directory": tmp_dir, "collection_name": "demo"})
        assert res4["status"] == "error", res4

        print("All self-tests passed successfully!")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
