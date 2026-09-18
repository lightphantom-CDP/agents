#!/usr/bin/env python3
"""
Policy RAG using Qdrant + OpenAI embeddings.

Two modes (pick one):
  A) Local embedded Qdrant (recommended on CAI — no separate Application)
     export QDRANT_PATH=medishield_policy_qdrant
     # stored under project dir (Sessions) or WORKFLOW_DATA_DIRECTORY (Agent Studio)
  B) Remote Qdrant server (Docker app or external)
     export QDRANT_URL=https://qdrant.your-domain

Setup:
  export OPENAI_API_KEY=sk-...
  pip install qdrant-client openai

Index (once):
  python3 agent/qdrant_policy_rag.py --index

Search:
  python3 agent/qdrant_policy_rag.py --query "prior auth standard plan"
"""

from __future__ import annotations

import argparse
import os
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "data" / "policy" / "coverage_policy.md"
DEFAULT_COLLECTION = "medishield-policy"
DEFAULT_EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536  # text-embedding-3-small
DEFAULT_LOCAL_DIR = "medishield_policy_qdrant"


def storage_root() -> Path:
    """Writable base dir for local Qdrant. Sessions lack /workflow_data."""
    explicit = os.environ.get("WORKFLOW_DATA_DIRECTORY", "").strip()
    if explicit:
        return Path(explicit)

    project = os.environ.get("CDSW_PROJECT", "").strip()
    if project:
        return Path(f"/home/cdsw/{project}")

    return ROOT


def resolve_qdrant_path(path: str | None = None) -> Path | None:
    raw = path or os.getenv("QDRANT_PATH", DEFAULT_LOCAL_DIR)
    if not raw:
        return None
    p = Path(raw)
    if p.is_absolute():
        return p
    return storage_root() / raw


def ensure_storage_dir(path: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        project = os.environ.get("CDSW_PROJECT", "insuranceclaim")
        raise PermissionError(
            f"Cannot write Qdrant data to {path}: {exc}. "
            f"Set an absolute path, e.g. "
            f"QDRANT_PATH=/home/cdsw/{project}/medishield_policy_qdrant"
        ) from exc
    return path


def get_qdrant_url() -> str:
    return os.getenv("QDRANT_URL", "").rstrip("/")


def chunk_policy(text: str, max_chars: int = 800) -> list[dict]:
    """Split policy by markdown sections."""
    chunks: list[dict] = []
    sections = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    for section in sections:
        section = section.strip()
        if not section:
            continue
        title_match = re.match(r"^## (.+)", section)
        title = title_match.group(1) if title_match else "intro"
        if len(section) <= max_chars:
            chunks.append({"section": title, "text": section})
        else:
            paragraphs = section.split("\n\n")
            buf = ""
            for para in paragraphs:
                if len(buf) + len(para) + 2 > max_chars and buf:
                    chunks.append({"section": title, "text": buf.strip()})
                    buf = para
                else:
                    buf = f"{buf}\n\n{para}" if buf else para
            if buf.strip():
                chunks.append({"section": title, "text": buf.strip()})
    return chunks


def embed_texts(texts: list[str], model: str = DEFAULT_EMBED_MODEL) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.embeddings.create(input=texts, model=model)
    return [item.embedding for item in response.data]


def _bypass_proxy_for_localhost(url: str) -> None:
    """CAI clusters often set HTTP_PROXY; httpx then fails on 127.0.0.1 (curl still works)."""
    if "127.0.0.1" in url or "localhost" in url:
        existing = os.environ.get("NO_PROXY", "")
        extras = "127.0.0.1,localhost"
        os.environ["NO_PROXY"] = f"{existing},{extras}" if existing else extras
        os.environ["no_proxy"] = os.environ["NO_PROXY"]


def get_client():
    from qdrant_client import QdrantClient

    url = get_qdrant_url()
    if url:
        _bypass_proxy_for_localhost(url)
        api_key = os.getenv("QDRANT_API_KEY")
        return QdrantClient(url=url, api_key=api_key, check_compatibility=False)

    local_path = resolve_qdrant_path()
    if local_path is None:
        raise ValueError("Set QDRANT_URL (remote) or QDRANT_PATH (local embedded Qdrant)")
    ensure_storage_dir(local_path)
    return QdrantClient(path=str(local_path), check_compatibility=False)


def search_collection(
    client,
    collection_name: str,
    query_vector: list[float],
    top_k: int = 3,
) -> list:
    """Works with qdrant-client 1.9 (search) and 1.19+ (query_points)."""
    if hasattr(client, "search"):
        return client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
        )
    result = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=top_k,
    )
    return result.points


def client_location() -> str:
    url = get_qdrant_url()
    if url:
        return url
    return str(resolve_qdrant_path())


def ensure_collection(client, collection_name: str) -> None:
    from qdrant_client.models import Distance, VectorParams

    names = [c.name for c in client.get_collections().collections]
    if collection_name in names:
        client.delete_collection(collection_name)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )


def index_policy(
    policy_path: str | Path = DEFAULT_POLICY,
    collection_name: str = DEFAULT_COLLECTION,
) -> int:
    """Index coverage_policy.md into Qdrant. Returns chunk count."""
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("Set OPENAI_API_KEY for embeddings")

    text = Path(policy_path).read_text(encoding="utf-8")
    chunks = chunk_policy(text)
    if not chunks:
        raise ValueError(f"No chunks from {policy_path}")

    vectors = embed_texts([c["text"] for c in chunks])
    client = get_client()
    ensure_collection(client, collection_name)

    from qdrant_client.models import PointStruct

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vectors[i],
            payload={"section": c["section"], "text": c["text"]},
        )
        for i, c in enumerate(chunks)
    ]
    client.upsert(collection_name=collection_name, points=points)
    print(f"Indexed {len(points)} chunks into '{collection_name}' at {client_location()}")
    return len(points)


def search_policy(
    query: str,
    collection_name: str = DEFAULT_COLLECTION,
    top_k: int = 3,
) -> list[dict]:
    """Search policy chunks. Returns list of {section, text, score}."""
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("Set OPENAI_API_KEY for embeddings")

    query_vector = embed_texts([query])[0]
    client = get_client()
    hits = search_collection(client, collection_name, query_vector, top_k)
    return [
        {
            "section": hit.payload.get("section", ""),
            "text": hit.payload.get("text", ""),
            "score": round(hit.score, 4),
        }
        for hit in hits
    ]


def format_policy_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[Policy chunk {i} | {c['section']} | score={c['score']}]\n{c['text']}")
    return "\n\n---\n\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Qdrant policy RAG for insurance demo")
    parser.add_argument("--index", action="store_true", help="Index coverage_policy.md")
    parser.add_argument("--query", default="", help="Search query")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    args = parser.parse_args()

    if args.index:
        index_policy(args.policy, args.collection)
    elif args.query:
        results = search_policy(args.query, args.collection)
        print(format_policy_context(results))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
