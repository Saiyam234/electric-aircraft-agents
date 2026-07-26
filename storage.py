"""Shared storage layer: wraps Cloudflare D1, Vectorize, and R2 behind plain functions.

Every agent goes through this module instead of calling the Cloudflare APIs
directly, so query structure, embedding calls, and versioning stay consistent
across the whole agent roster.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, TypedDict

import requests
from dotenv import load_dotenv

from config import (
    ASSURANCE_OFFICES,
    CF_API_BASE,
    EMBEDDING_MODEL,
    GET_BY_IDS_MAX_BATCH,
    MAX_BASELINE_CONFIG_BYTES,
    MAX_REQUIREMENT_TEXT_LENGTH,
    MAX_SIGNOFF_NOTES_LENGTH,
    MIN_REQUIREMENT_TEXT_LENGTH,
)

load_dotenv()

logger = logging.getLogger(__name__)

ACCOUNT_ID = os.environ["CLOUDFLARE_ACCOUNT_ID"]
API_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]
D1_DATABASE_ID = os.environ["CLOUDFLARE_D1_DATABASE_ID"]
VECTORIZE_INDEX_NAME = os.environ["CLOUDFLARE_VECTORIZE_INDEX_NAME"]
R2_BUCKET_NAME = os.environ.get("CLOUDFLARE_R2_BUCKET_NAME")

_HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}


# ---------------------------------------------------------------------------
# Return-shape types
# ---------------------------------------------------------------------------

class BaselineRow(TypedDict):
    id: int
    version: str
    status: str
    created_at: str


class SignoffRow(TypedDict):
    office: str
    signed_off_at: str | None
    notes: str


class BaselineDetail(TypedDict):
    id: int
    version: str
    status: str
    config: dict
    created_at: str
    signoffs: list[SignoffRow]


class AuditLogRow(TypedDict):
    id: int
    timestamp: str
    agent: str
    event_type: str
    description: str
    related_baseline_id: int | None
    related_requirement_id: int | None


class KBMetadata(TypedDict, total=False):
    text: str
    topic: str
    source_url: str
    source_title: str


class KBSearchMatch(TypedDict):
    id: str
    score: float
    metadata: KBMetadata


class KBEntry(TypedDict):
    id: str
    namespace: str | None
    metadata: KBMetadata
    values: list[float]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CloudflareAPIError(RuntimeError):
    pass


class R2NotEnabledError(RuntimeError):
    pass


def _request(method: str, url: str, max_retries: int = 3, **kwargs) -> requests.Response:
    """requests.request with retry-with-backoff on network errors, 429, and 5xx.

    Client errors (4xx other than 429) are not retried — those indicate a bad
    request, not a transient failure, and retrying would just fail the same way.

    Only method/URL/status/attempt number are ever logged — never headers or
    body, so the bearer token and any request/response payloads never end up
    in logs.
    """
    last_exc: Exception | None = None
    resp: requests.Response | None = None
    for attempt in range(1, max_retries + 1):
        logger.debug("Request attempt %d/%d: %s %s", attempt, max_retries, method, url)
        try:
            resp = requests.request(method, url, timeout=30, **kwargs)
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            backoff = 2 ** (attempt - 1)
            logger.warning(
                "Attempt %d/%d network error for %s %s: %s — retrying in %ds",
                attempt, max_retries, method, url, exc, backoff,
            )
            time.sleep(backoff)
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            backoff = 2 ** (attempt - 1)
            logger.warning(
                "Attempt %d/%d got status %d for %s %s — retrying in %ds",
                attempt, max_retries, resp.status_code, method, url, backoff,
            )
            time.sleep(backoff)
            continue
        return resp
    if resp is not None:
        logger.error(
            "All %d attempts exhausted for %s %s, last status %d", max_retries, method, url, resp.status_code
        )
        return resp
    logger.error("All %d attempts failed for %s %s: %s", max_retries, method, url, last_exc)
    raise CloudflareAPIError(f"Request to {url} failed after {max_retries} attempts: {last_exc}")


# ---------------------------------------------------------------------------
# D1
# ---------------------------------------------------------------------------

def _d1_query(sql: str, params: list[Any] | None = None) -> list[dict]:
    url = f"{CF_API_BASE}/accounts/{ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}/query"
    resp = _request("POST", url, headers=_HEADERS, json={"sql": sql, "params": params or []})
    resp.raise_for_status()
    data = resp.json()
    if not data["success"]:
        logger.error("D1 query failed: %s", data["errors"])
        raise CloudflareAPIError(f"D1 query failed: {data['errors']}")
    return data["result"][0]["results"]


SCHEMA = """
CREATE TABLE IF NOT EXISTS baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft',
    config TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS baseline_signoffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    baseline_id INTEGER NOT NULL REFERENCES baselines(id),
    office TEXT NOT NULL CHECK (office IN ('review_critic', 'safety_risk', 'regulatory')),
    signed_off_at TEXT,
    notes TEXT,
    UNIQUE(baseline_id, office)
);
CREATE TABLE IF NOT EXISTS requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed',
    baseline_id INTEGER REFERENCES baselines(id),
    impact_assessment TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent TEXT NOT NULL,
    event_type TEXT NOT NULL,
    description TEXT NOT NULL,
    related_baseline_id INTEGER REFERENCES baselines(id),
    related_requirement_id INTEGER REFERENCES requirements(id)
);
"""


def init_db() -> None:
    for statement in filter(None, (s.strip() for s in SCHEMA.split(";"))):
        _d1_query(statement)


def create_baseline(config: dict, version: str | None = None) -> int:
    if not isinstance(config, dict):
        raise TypeError(f"config must be a dict, got {type(config).__name__}")
    serialized = json.dumps(config)
    size = len(serialized.encode("utf-8"))
    if size > MAX_BASELINE_CONFIG_BYTES:
        raise ValueError(f"config is {size} bytes, exceeds the {MAX_BASELINE_CONFIG_BYTES}-byte limit")

    version = version or f"v{int(time.time())}"
    _d1_query(
        "INSERT INTO baselines (version, status, config, created_at) VALUES (?, ?, ?, ?)",
        [version, "draft", serialized, _now()],
    )
    return _d1_query("SELECT id FROM baselines WHERE version = ?", [version])[0]["id"]


def list_baselines(limit: int = 50) -> list[BaselineRow]:
    """Lightweight listing (no config blob) for project-state tracking/reporting."""
    return _d1_query(
        "SELECT id, version, status, created_at FROM baselines ORDER BY created_at DESC LIMIT ?",
        [limit],
    )


def get_baseline(baseline_id: int) -> BaselineDetail:
    rows = _d1_query("SELECT * FROM baselines WHERE id = ?", [baseline_id])
    if not rows:
        raise ValueError(f"No baseline with id {baseline_id}")
    baseline = rows[0]
    baseline["config"] = json.loads(baseline["config"])
    baseline["signoffs"] = _d1_query(
        "SELECT office, signed_off_at, notes FROM baseline_signoffs WHERE baseline_id = ?",
        [baseline_id],
    )
    return baseline


def record_signoff(baseline_id: int, office: str, notes: str = "") -> None:
    if office not in ASSURANCE_OFFICES:
        raise ValueError(f"office must be one of {ASSURANCE_OFFICES}, got {office!r}")
    if len(notes) > MAX_SIGNOFF_NOTES_LENGTH:
        raise ValueError(f"notes must be at most {MAX_SIGNOFF_NOTES_LENGTH} chars, got {len(notes)}")
    _d1_query(
        """
        INSERT INTO baseline_signoffs (baseline_id, office, signed_off_at, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(baseline_id, office)
        DO UPDATE SET signed_off_at = excluded.signed_off_at, notes = excluded.notes
        """,
        [baseline_id, office, _now(), notes],
    )


def is_baseline_stamped(baseline_id: int) -> bool:
    rows = _d1_query(
        "SELECT office FROM baseline_signoffs WHERE baseline_id = ? AND signed_off_at IS NOT NULL",
        [baseline_id],
    )
    signed = {r["office"] for r in rows}
    return ASSURANCE_OFFICES.issubset(signed)


def add_requirement(text: str, baseline_id: int | None = None, impact_assessment: str | None = None) -> int:
    if not (MIN_REQUIREMENT_TEXT_LENGTH <= len(text) <= MAX_REQUIREMENT_TEXT_LENGTH):
        raise ValueError(
            f"text must be {MIN_REQUIREMENT_TEXT_LENGTH}-{MAX_REQUIREMENT_TEXT_LENGTH} chars, got {len(text)}"
        )
    now = _now()
    _d1_query(
        """
        INSERT INTO requirements (text, status, baseline_id, impact_assessment, created_at, updated_at)
        VALUES (?, 'proposed', ?, ?, ?, ?)
        """,
        [text, baseline_id, impact_assessment, now, now],
    )
    return _d1_query("SELECT id FROM requirements ORDER BY id DESC LIMIT 1")[0]["id"]


def update_requirement_status(requirement_id: int, status: str) -> None:
    _d1_query(
        "UPDATE requirements SET status = ?, updated_at = ? WHERE id = ?",
        [status, _now(), requirement_id],
    )


def log_event(
    agent: str,
    event_type: str,
    description: str,
    related_baseline_id: int | None = None,
    related_requirement_id: int | None = None,
) -> None:
    _d1_query(
        """
        INSERT INTO audit_log (timestamp, agent, event_type, description, related_baseline_id, related_requirement_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [_now(), agent, event_type, description, related_baseline_id, related_requirement_id],
    )


def get_audit_log(limit: int = 50) -> list[AuditLogRow]:
    return _d1_query("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", [limit])


# ---------------------------------------------------------------------------
# Vectorize + Workers AI (semantic search over the knowledge base)
# ---------------------------------------------------------------------------

def _embed(texts: list[str]) -> list[list[float]]:
    url = f"{CF_API_BASE}/accounts/{ACCOUNT_ID}/ai/run/{EMBEDDING_MODEL}"
    resp = _request("POST", url, headers=_HEADERS, json={"text": texts})
    resp.raise_for_status()
    data = resp.json()
    if not data["success"]:
        logger.error("Workers AI embedding failed: %s", data["errors"])
        raise CloudflareAPIError(f"Workers AI embedding failed: {data['errors']}")
    return data["result"]["data"]


def upsert_kb(entry_id: str, text: str, metadata: dict | None = None) -> None:
    vector = _embed([text])[0]
    ndjson = json.dumps({"id": entry_id, "values": vector, "metadata": {**(metadata or {}), "text": text}})
    url = f"{CF_API_BASE}/accounts/{ACCOUNT_ID}/vectorize/v2/indexes/{VECTORIZE_INDEX_NAME}/upsert"
    resp = _request("POST", url, headers={**_HEADERS, "Content-Type": "application/x-ndjson"}, data=ndjson)
    resp.raise_for_status()
    data = resp.json()
    if not data["success"]:
        logger.error("Vectorize upsert failed: %s", data["errors"])
        raise CloudflareAPIError(f"Vectorize upsert failed: {data['errors']}")


def search_kb(query: str, top_k: int = 5) -> list[KBSearchMatch]:
    vector = _embed([query])[0]
    url = f"{CF_API_BASE}/accounts/{ACCOUNT_ID}/vectorize/v2/indexes/{VECTORIZE_INDEX_NAME}/query"
    resp = _request("POST", url, headers=_HEADERS, json={"vector": vector, "topK": top_k, "returnMetadata": "all"})
    resp.raise_for_status()
    data = resp.json()
    if not data["success"]:
        logger.error("Vectorize query failed: %s", data["errors"])
        raise CloudflareAPIError(f"Vectorize query failed: {data['errors']}")
    return data["result"]["matches"]


def list_kb_ids(limit: int = 1000) -> list[str]:
    """Paginates through every vector ID currently in the KB index.

    Vectorize is eventually consistent, and this endpoint lags further behind
    a fresh upsert than search_kb does (~20s+ observed vs. ~15s for search_kb) —
    don't upsert_kb and immediately list_kb_ids in the same run expecting to
    see it; search_kb catches up faster if that's all you need.
    """
    ids: list[str] = []
    cursor = None
    url = f"{CF_API_BASE}/accounts/{ACCOUNT_ID}/vectorize/v2/indexes/{VECTORIZE_INDEX_NAME}/list"
    while len(ids) < limit:
        params = {"count": min(100, limit - len(ids))}
        if cursor:
            params["cursor"] = cursor
        resp = _request("GET", url, headers=_HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not data["success"]:
            logger.error("Vectorize list failed: %s", data["errors"])
            raise CloudflareAPIError(f"Vectorize list failed: {data['errors']}")
        result = data["result"]
        ids.extend(v["id"] for v in result["vectors"])
        cursor = result.get("nextCursor")
        if not result.get("isTruncated") or not cursor:
            break
    return ids[:limit]


def get_kb_entries(ids: list[str]) -> list[KBEntry]:
    """Fetches full vector data (metadata + embedding values) for any number of IDs.

    Batches internally since Vectorize's get_by_ids caps at 20 IDs per call.
    """
    url = f"{CF_API_BASE}/accounts/{ACCOUNT_ID}/vectorize/v2/indexes/{VECTORIZE_INDEX_NAME}/get_by_ids"
    entries: list[KBEntry] = []
    for i in range(0, len(ids), GET_BY_IDS_MAX_BATCH):
        batch = ids[i : i + GET_BY_IDS_MAX_BATCH]
        resp = _request("POST", url, headers=_HEADERS, json={"ids": batch})
        resp.raise_for_status()
        data = resp.json()
        if not data["success"]:
            logger.error("Vectorize get_by_ids failed: %s", data["errors"])
            raise CloudflareAPIError(f"Vectorize get_by_ids failed: {data['errors']}")
        entries.extend(data["result"])
    return entries


def delete_kb_entries(ids: list[str]) -> None:
    """Deletes vectors by ID. Vectorize deletes are async (best-effort, not
    guaranteed to be immediately reflected in subsequent list/search calls).
    """
    if not ids:
        return
    url = f"{CF_API_BASE}/accounts/{ACCOUNT_ID}/vectorize/v2/indexes/{VECTORIZE_INDEX_NAME}/delete_by_ids"
    resp = _request("POST", url, headers=_HEADERS, json={"ids": ids})
    resp.raise_for_status()
    data = resp.json()
    if not data["success"]:
        logger.error("Vectorize delete_by_ids failed: %s", data["errors"])
        raise CloudflareAPIError(f"Vectorize delete_by_ids failed: {data['errors']}")


# ---------------------------------------------------------------------------
# R2 (files) — not usable until the R2 subscription is enabled on the account
# ---------------------------------------------------------------------------

def upload_file(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    if not R2_BUCKET_NAME:
        raise R2NotEnabledError("CLOUDFLARE_R2_BUCKET_NAME not set")
    url = f"{CF_API_BASE}/accounts/{ACCOUNT_ID}/r2/buckets/{R2_BUCKET_NAME}/objects/{key}"
    resp = _request("PUT", url, headers={**_HEADERS, "Content-Type": content_type}, data=data)
    if "10042" in resp.text:
        raise R2NotEnabledError("R2 is not enabled on this account yet")
    resp.raise_for_status()


def get_file(key: str) -> bytes:
    if not R2_BUCKET_NAME:
        raise R2NotEnabledError("CLOUDFLARE_R2_BUCKET_NAME not set")
    url = f"{CF_API_BASE}/accounts/{ACCOUNT_ID}/r2/buckets/{R2_BUCKET_NAME}/objects/{key}"
    resp = _request("GET", url, headers=_HEADERS)
    if "10042" in resp.text:
        raise R2NotEnabledError("R2 is not enabled on this account yet")
    resp.raise_for_status()
    return resp.content
