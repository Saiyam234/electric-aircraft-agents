"""Regression tests for storage.py against the REAL Cloudflare account.

These are integration tests, not mocks — real D1/Vectorize calls, real
(tiny) cost. Each test cleans up its own data afterward via fixtures. This
covers the storage layer's own behavior; agents are validated separately by
running them for real and checking outcomes against ground truth, since
their correctness is about judgment quality, not deterministic functions.

Run with: pytest test_storage.py -v
"""

import time
import uuid

import pytest

import storage

TEST_PREFIX = "pytest"


def _unique(suffix: str) -> str:
    return f"{TEST_PREFIX}-{suffix}-{uuid.uuid4().hex[:8]}"


def _wait_until(predicate, timeout: float = 240.0, interval: float = 5.0):
    """Polls predicate() until it returns truthy or timeout elapses.

    Vectorize is eventually consistent with highly variable lag — a fixed
    sleep is the wrong tool, so poll instead.

    On the observed lag: normally ~15-45s, but a measured 189s was seen right
    after a bulk delete (alongside genuine read timeouts from the Cloudflare
    API), presumably while the index reorganised. The timeout is set well
    above that worst case deliberately. It costs nothing on a healthy
    service, because this returns the moment the predicate passes — it only
    buys patience during a degraded window, which is exactly when a short
    ceiling would produce a false failure and send someone hunting a bug that
    isn't in this repo.
    """
    deadline = time.time() + timeout
    result = predicate()
    while not result and time.time() < deadline:
        time.sleep(interval)
        result = predicate()
    return result


@pytest.fixture
def baseline_id():
    bid = storage.create_baseline({"note": "pytest test baseline"}, version=_unique("baseline"))
    yield bid
    storage._d1_query("DELETE FROM baseline_signoffs WHERE baseline_id = ?", [bid])
    storage._d1_query("DELETE FROM requirements WHERE baseline_id = ?", [bid])
    storage._d1_query("DELETE FROM audit_log WHERE related_baseline_id = ?", [bid])
    storage._d1_query("DELETE FROM baselines WHERE id = ?", [bid])


def test_create_and_get_baseline(baseline_id):
    baseline = storage.get_baseline(baseline_id)
    assert baseline["config"] == {"note": "pytest test baseline"}
    assert baseline["status"] == "draft"
    assert baseline["signoffs"] == []


def test_list_baselines_includes_new_one(baseline_id):
    baseline = storage.get_baseline(baseline_id)
    versions = [b["version"] for b in storage.list_baselines(limit=200)]
    assert baseline["version"] in versions


def test_create_baseline_rejects_non_dict_config():
    with pytest.raises(TypeError):
        storage.create_baseline(["not", "a", "dict"], version=_unique("baseline"))


def test_create_baseline_rejects_oversized_config():
    huge_config = {"blob": "x" * (storage.MAX_BASELINE_CONFIG_BYTES + 1)}
    with pytest.raises(ValueError):
        storage.create_baseline(huge_config, version=_unique("baseline"))


def test_add_requirement_rejects_empty_text(baseline_id):
    with pytest.raises(ValueError):
        storage.add_requirement("", baseline_id=baseline_id)


def test_add_requirement_rejects_oversized_text(baseline_id):
    with pytest.raises(ValueError):
        storage.add_requirement("x" * (storage.MAX_REQUIREMENT_TEXT_LENGTH + 1), baseline_id=baseline_id)


def test_record_signoff_rejects_oversized_notes(baseline_id):
    with pytest.raises(ValueError):
        storage.record_signoff(baseline_id, "review_critic", notes="x" * (storage.MAX_SIGNOFF_NOTES_LENGTH + 1))


def test_signoff_stamping_requires_all_three_offices(baseline_id):
    assert storage.is_baseline_stamped(baseline_id) is False
    storage.record_signoff(baseline_id, "review_critic")
    storage.record_signoff(baseline_id, "safety_risk")
    assert storage.is_baseline_stamped(baseline_id) is False
    storage.record_signoff(baseline_id, "regulatory")
    assert storage.is_baseline_stamped(baseline_id) is True


def test_signoff_rejects_invalid_office(baseline_id):
    with pytest.raises(ValueError):
        storage.record_signoff(baseline_id, "not_a_real_office")


def test_requirement_lifecycle(baseline_id):
    req_id = storage.add_requirement("pytest test requirement", baseline_id=baseline_id)
    rows = storage._d1_query("SELECT status FROM requirements WHERE id = ?", [req_id])
    assert rows[0]["status"] == "proposed"

    storage.update_requirement_status(req_id, "approved")
    rows = storage._d1_query("SELECT status FROM requirements WHERE id = ?", [req_id])
    assert rows[0]["status"] == "approved"


def test_list_requirements(baseline_id):
    text = f"pytest requirement {_unique('req')}"
    req_id = storage.add_requirement(text, baseline_id=baseline_id)

    # Unfiltered listing should surface it
    all_reqs = storage.list_requirements(limit=200)
    assert any(r["id"] == req_id and r["text"] == text for r in all_reqs)

    # Filtered to this baseline, it should be the only one
    scoped = storage.list_requirements(baseline_id=baseline_id)
    assert [r["id"] for r in scoped] == [req_id]
    assert scoped[0]["status"] == "proposed"
    assert scoped[0]["baseline_id"] == baseline_id


def test_list_requirements_filters_by_baseline(baseline_id):
    storage.add_requirement("pytest requirement attached to a baseline", baseline_id=baseline_id)
    other = storage.list_requirements(baseline_id=baseline_id + 10_000_000)
    assert other == []


def test_log_event_and_get_audit_log(baseline_id):
    marker = _unique("event")
    storage.log_event("pytest", "test_event", marker, related_baseline_id=baseline_id)
    recent = storage.get_audit_log(limit=10)
    assert any(e["description"] == marker for e in recent)


@pytest.fixture
def kb_entry_id():
    entry_id = _unique("kb")
    storage.upsert_kb(entry_id, "pytest test fact: the sky is blue due to Rayleigh scattering", {"topic": "pytest"})
    yield entry_id
    storage.delete_kb_entries([entry_id])


def test_upsert_and_search_kb(kb_entry_id):
    def found():
        ids = [r["id"] for r in storage.search_kb("why is the sky blue", top_k=5)]
        return kb_entry_id in ids

    assert _wait_until(found), f"{kb_entry_id} never appeared in search_kb results within timeout"


def test_list_kb_ids_and_get_kb_entries(kb_entry_id):
    assert _wait_until(lambda: kb_entry_id in storage.list_kb_ids()), (
        f"{kb_entry_id} never appeared in list_kb_ids within timeout"
    )

    entries = storage.get_kb_entries([kb_entry_id])
    assert len(entries) == 1
    assert entries[0]["metadata"]["topic"] == "pytest"


def test_upsert_kb_checked_rejects_duplicate(kb_entry_id):
    # Vectorize's get_by_ids consistency is unreliable enough (see
    # storage._kb_entry_exists) that even upsert_kb_checked's own internal
    # retry budget (~20s) can occasionally lose the race. Retry the whole
    # assertion rather than treating one slow window as a real failure --
    # if it's a genuine bug (never detects the duplicate), this still fails
    # once the generous timeout below is exhausted.
    def raises_duplicate() -> bool:
        try:
            storage.upsert_kb_checked(kb_entry_id, "completely different text")
        except ValueError as exc:
            return "already exists" in str(exc)
        return False

    assert _wait_until(raises_duplicate, timeout=300.0, interval=20.0), (
        f"upsert_kb_checked never raised for existing entry {kb_entry_id} within timeout"
    )


def test_upsert_kb_checked_creates_new():
    entry_id = _unique("kb-checked")
    result = storage.upsert_kb_checked(entry_id, "pytest fact for checked upsert", {"topic": "pytest"})
    assert result == {"status": "created", "entry_id": entry_id}
    assert _wait_until(lambda: entry_id in storage.list_kb_ids()), f"{entry_id} not found after upsert"
    storage.delete_kb_entries([entry_id])
