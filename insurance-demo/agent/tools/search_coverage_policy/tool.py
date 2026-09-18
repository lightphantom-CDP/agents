"""
Agent Studio Tool — search MediShield policy via local Qdrant + OpenAI embeddings.

Self-contained (does NOT import agent.qdrant_policy_rag).
Auto-indexes coverage_policy.md on first run inside the Agent Studio pod.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

OUTPUT_KEY = "tool_output"
DEFAULT_COLLECTION = "medishield-policy"
DEFAULT_EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536
DEFAULT_LOCAL_DIR = "medishield_policy_qdrant"

# Embedded policy fallback — used when coverage_policy.md is not on disk
# (Agent Studio Tools Catalog often keeps only tool.py + requirements.txt).
# Keep in sync with data/policy/coverage_policy.md.
EMBEDDED_POLICY = """# MediShield Hospital Claims Policy (Demo)

Version: 2026.1
Audience: Medical claims review and AI agent reviewers

## 1. Purpose
This policy governs automated and manual decisions for inpatient, outpatient, and emergency hospital claims.

## 2. Covered services by plan

### Basic plan
- Annual limit: USD 15,000
- Waiting period: 90 days from coverage start
- Maternity, dental, mental health, and experimental treatments are excluded
- Prior authorization required for procedures over USD 3,000

### Standard plan
- Annual limit: USD 50,000
- Waiting period: 30 days
- Maternity and mental health covered; dental and experimental excluded
- Prior authorization required over USD 8,000

### Premium plan
- Annual limit: USD 200,000
- No waiting period
- Full coverage including maternity, dental, mental health, and approved experimental therapies
- Prior authorization required over USD 25,000

## 3. Automatic approval criteria
Approve when ALL of the following are true:
- Policy status is active
- Waiting period has elapsed
- Diagnosis and procedures are covered under the member plan
- Prior authorization is on file when billed amount exceeds plan threshold
- Total claim is within remaining annual limit
- No undisclosed pre-existing condition matches the primary diagnosis

## 4. Automatic rejection criteria
Reject when ANY of the following apply:
- Policy is lapsed or inactive
- Service date falls inside the waiting period
- Primary diagnosis relates to an undisclosed pre-existing condition
- Experimental treatment on Basic or Standard plans
- Maternity claim on a plan without maternity coverage
- Mental health claim on Basic plan

## 5. Manual review triggers
Route to clinical review when:
- Claim amount is between 60% and 90% of remaining annual limit
- Multiple high-cost procedures on the same admission
- Conflicting diagnosis and procedure codes
- Readmission within 7 days for the same diagnosis category
- An experimental treatment line requires clinical necessity review

## 6. Partial approval rules
- Apply partial approval when medically necessary services are mixed with excluded line items
- Document each excluded line item in the denial reasons
- Member pays deductible before insurer share is calculated

## 7. Emergency admission override
Emergency admissions may bypass prior authorization requirements, but:
- Documentation must confirm emergency presentation
- Experimental treatments remain excluded unless Premium plan
- Annual limit still applies

## 8. Claim review transparency
Every decision must cite specific policy sections and clinical factors.
Generic denials such as "not covered" without diagnosis or policy reference are not acceptable.

## 9. Model and agent governance
- Champion claim review model must be registered in Cloudera AI Registry
- Feature tables must be sourced from governed Iceberg gold tables only
- Agent decisions must include: outcome, approved amount, policy citations, and top risk factors
"""


class UserParameters(BaseModel):
    qdrant_url: str = Field(
        default="",
        description="Leave empty, or set local folder e.g. medishield_policy_qdrant",
    )
    qdrant_path: str = Field(default="")
    collection_name: str = Field(default=DEFAULT_COLLECTION)
    openai_api_key: str = Field(default="", description="OpenAI key for embeddings")


class ToolParameters(BaseModel):
    query: str = Field(description="Policy search query")
    top_k: int = Field(default=3)

    @field_validator("top_k", mode="before")
    @classmethod
    def coerce_top_k(cls, value: Any) -> int:
        if value in (None, ""):
            return 3
        return int(value)


def project_root() -> Path:
    return Path("/home/cdsw")


def safe_tool_dir() -> Path:
    """Agent Studio may exec tool code without __file__ — use known mount paths."""
    try:
        return Path(__file__).resolve().parent
    except NameError:
        pass
    project = os.environ.get("CDSW_PROJECT", "").strip()
    candidates = [
        Path("/tool"),
        Path.cwd(),
        Path.cwd() / "search_coverage_policy",
    ]
    if project:
        candidates.append(Path(f"/home/cdsw/{project}/agent/tools/search_coverage_policy"))
        candidates.append(Path(f"/home/cdsw/{project}/search_coverage_policy"))
    for path in candidates:
        if path.is_dir():
            return path
    return Path("/tool")


def storage_root() -> Path:
    explicit = os.environ.get("WORKFLOW_DATA_DIRECTORY", "").strip()
    if explicit:
        return Path(explicit)
    project = os.environ.get("CDSW_PROJECT", "").strip()
    if project:
        return Path(f"/home/cdsw/{project}")
    return project_root()


def is_http_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def policy_file_candidates() -> list[Path]:
    """Agent Studio mounts tools at /tool/tool.py — keep paths shallow and safe."""
    tool_dir = safe_tool_dir()
    root = project_root()
    cwd = Path.cwd()
    candidates = [
        tool_dir / "coverage_policy.md",
        Path("/tool/coverage_policy.md"),
        cwd / "coverage_policy.md",
        root / "coverage_policy.md",
        root / "data" / "policy" / "coverage_policy.md",
        tool_dir / "data" / "policy" / "coverage_policy.md",
        cwd / "data" / "policy" / "coverage_policy.md",
    ]
    seen: set[str] = set()
    unique: list[Path] = []
    for path in candidates:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def find_policy_file() -> Path | None:
    for path in policy_file_candidates():
        if path.exists():
            return path
    return None


def chunk_policy(text: str, max_chars: int = 800) -> list[dict]:
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


def embed_texts(texts: list[str], api_key: str) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(input=texts, model=DEFAULT_EMBED_MODEL)
    return [item.embedding for item in response.data]


def qdrant_dir_candidates(config: UserParameters) -> list[Path]:
    raw = (config.qdrant_url or "").strip()
    names: list[str] = []
    if raw and not is_http_url(raw):
        names.append(raw)
    if config.qdrant_path:
        names.append(config.qdrant_path)
    env_path = os.getenv("QDRANT_PATH", "").strip()
    if env_path:
        names.append(env_path)
    names.append(DEFAULT_LOCAL_DIR)

    seen: set[str] = set()
    candidates: list[Path] = []
    for name in names:
        path = Path(name)
        if path.is_absolute():
            key = str(path)
            if key not in seen:
                seen.add(key)
                candidates.append(path)
            continue
        for base in (storage_root(), project_root(), Path("/tmp")):
            candidate = base / name
            key = str(candidate)
            if key not in seen:
                seen.add(key)
                candidates.append(candidate)
    return candidates


def qdrant_dir_exists(path: Path) -> bool:
    return path.exists() and ((path / "meta.json").exists() or (path / "collection").exists())


def pick_qdrant_dir(config: UserParameters) -> Path:
    for path in qdrant_dir_candidates(config):
        if qdrant_dir_exists(path):
            return path
    for path in qdrant_dir_candidates(config):
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError:
            continue
    raise FileNotFoundError(
        "No writable Qdrant directory. Tried: "
        + ", ".join(str(p) for p in qdrant_dir_candidates(config))
    )


def ensure_collection(client, collection_name: str) -> None:
    from qdrant_client.models import Distance, VectorParams

    names = [c.name for c in client.get_collections().collections]
    if collection_name in names:
        client.delete_collection(collection_name)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
    )


def build_local_index(config: UserParameters, api_key: str, target: Path) -> None:
    if qdrant_dir_exists(target):
        return

    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct

    # Prefer an on-disk policy file; fall back to the embedded copy so the tool
    # works even when Agent Studio didn't bundle coverage_policy.md.
    policy = find_policy_file()
    if policy is not None:
        text = policy.read_text(encoding="utf-8")
        source = str(policy)
    else:
        text = EMBEDDED_POLICY
        source = "embedded"

    chunks = chunk_policy(text)
    if not chunks:
        raise ValueError(f"No chunks parsed from policy ({source})")

    vectors = embed_texts([c["text"] for c in chunks], api_key)
    client = QdrantClient(path=str(target), check_compatibility=False)
    ensure_collection(client, config.collection_name)

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vectors[i],
            payload={"section": c["section"], "text": c["text"]},
        )
        for i, c in enumerate(chunks)
    ]
    client.upsert(collection_name=config.collection_name, points=points)


def get_qdrant_client(config: UserParameters, api_key: str):
    from qdrant_client import QdrantClient

    raw = (config.qdrant_url or os.getenv("QDRANT_URL", "")).strip().rstrip("/")
    if raw and is_http_url(raw):
        if "127.0.0.1" in raw or "localhost" in raw:
            os.environ["NO_PROXY"] = "127.0.0.1,localhost"
        return QdrantClient(
            url=raw,
            api_key=os.getenv("QDRANT_API_KEY"),
            check_compatibility=False,
        )

    target = pick_qdrant_dir(config)
    if not qdrant_dir_exists(target):
        build_local_index(config, api_key, target)
    return QdrantClient(path=str(target), check_compatibility=False)


def search_collection(client, collection_name: str, query_vector: list[float], top_k: int):
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


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    api_key = config.openai_api_key or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {"error": "Set openai_api_key in tool configuration"}

    top_k = args.top_k or 3
    if not args.query.strip():
        return {"error": "query is required, e.g. 'pre-existing condition rejection rules'"}

    try:
        client = get_qdrant_client(config, api_key)
        vector = embed_texts([args.query], api_key)[0]
        hits = search_collection(client, config.collection_name, vector, top_k)
        storage = str(pick_qdrant_dir(config))
    except Exception as exc:
        try:
            policy_paths = [str(p) for p in policy_file_candidates()]
        except Exception:
            policy_paths = [str(safe_tool_dir() / "coverage_policy.md")]
        try:
            qdrant_paths = [str(p) for p in qdrant_dir_candidates(config)]
        except Exception:
            qdrant_paths = []
        return {
            "error": f"{type(exc).__name__}: {exc}",
            "hint": (
                "Upload coverage_policy.md into the tool folder (same folder as tool.py), "
                "set openai_api_key, leave qdrant_url empty, top_k=3"
            ),
            "policy_candidates": policy_paths,
            "qdrant_candidates": qdrant_paths,
        }

    chunks = [
        {
            "section": (hit.payload or {}).get("section", ""),
            "text": (hit.payload or {}).get("text", ""),
            "score": round(hit.score, 4),
        }
        for hit in hits
    ]
    return {
        "query": args.query,
        "collection": config.collection_name,
        "storage": storage,
        "chunks": chunks,
        "policy_excerpt": "\n\n---\n\n".join(
            f"[{c['section']}] {c['text']}" for c in chunks
        ),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--user-params", required=True)
    parser.add_argument("--tool-params", required=True)
    cli_args = parser.parse_args()

    user_config = UserParameters(**json.loads(cli_args.user_params))
    tool_args = ToolParameters(**json.loads(cli_args.tool_params))
    result = run_tool(user_config, tool_args)
    print(OUTPUT_KEY, json.dumps(result, indent=2, default=str))
