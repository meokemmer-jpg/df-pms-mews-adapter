"""W41-A Idempotency-Integration-Tests fuer mews-pms book_room [CRUX-MK]."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _df_common.idempotency_keys import IdempotencyStore  # noqa: E402
from _df_common.idempotency_adapter_wrapper import (  # noqa: E402
    idempotency_check,
    store_cached_response,
)
from src.mews_adapter import MEWSConnector  # noqa: E402


@pytest.fixture
def store(tmp_path):
    return IdempotencyStore(db_path=tmp_path / "idem.db")


@pytest.fixture
def adapter():
    a = MEWSConnector(sandbox_mode=True)
    a.connect({"client_token": "test", "access_token": "test"})
    return a


def _book_with_idempotency(adapter, store, response_db, payload):
    """Hilfs-Wrapper: book_room mit Idempotency-Check."""
    result = idempotency_check(
        tenant_id=payload["hotel_id"],
        adapter_name=adapter.adapter_name,
        operation="book_room",
        payload=payload,
        store=store,
        response_db=response_db,
    )
    if result.status == "duplicate" and result.cached_response is not None:
        return result.cached_response, "cached"
    booking_id = adapter.book_room(
        payload["hotel_id"], payload["room_type"],
        {"email": payload["guest_email"]}, tuple(payload["dates"]),
    )
    response = {"booking_id": booking_id, "adapter": adapter.adapter_name}
    store_cached_response(response_db, result.key_hash, response)
    return response, "fresh"


def test_duplicate_call_returns_cached(adapter, store, tmp_path):
    """1. book_room: fresh + booking_id. 2. book_room (gleicher Payload): cached."""
    payload = {
        "hotel_id": "hildesheim", "room_type": "deluxe",
        "guest_email": "test@kemmer.de", "dates": ["2026-06-01", "2026-06-02"],
    }
    response_db = tmp_path / "resp.db"

    r1, s1 = _book_with_idempotency(adapter, store, response_db, payload)
    r2, s2 = _book_with_idempotency(adapter, store, response_db, payload)

    assert s1 == "fresh"
    assert s2 == "cached"
    assert r1["booking_id"] == r2["booking_id"]
    assert r1["booking_id"].startswith("mews-mock-")


def test_different_keys_independent(adapter, store, tmp_path):
    """Unterschiedliche Hotels/Daten -> unabhaengige Buchungen."""
    response_db = tmp_path / "resp.db"
    p_a = {"hotel_id": "hildesheim", "room_type": "std",
           "guest_email": "a@x.de", "dates": ["2026-06-01", "2026-06-02"]}
    p_b = {"hotel_id": "munich", "room_type": "std",
           "guest_email": "a@x.de", "dates": ["2026-06-01", "2026-06-02"]}
    r_a, s_a = _book_with_idempotency(adapter, store, response_db, p_a)
    r_b, s_b = _book_with_idempotency(adapter, store, response_db, p_b)
    assert s_a == s_b == "fresh"
    assert r_a["booking_id"] != r_b["booking_id"]


def test_expired_key_recomputes(adapter, store, tmp_path):
    """Nach TTL-Ablauf: erneut 'fresh' + neuer real-call."""
    import time as _t
    payload = {"hotel_id": "munich", "room_type": "suite",
               "guest_email": "x@y.de", "dates": ["2026-07-01", "2026-07-02"]}
    response_db = tmp_path / "resp.db"

    # 1. Call mit kurzer TTL
    res = idempotency_check(
        tenant_id=payload["hotel_id"], adapter_name=adapter.adapter_name,
        operation="book_room", payload=payload, ttl_seconds=1, store=store,
    )
    assert res.status == "fresh"
    _t.sleep(1.5)
    # 2. Call nach TTL: wieder fresh
    res2 = idempotency_check(
        tenant_id=payload["hotel_id"], adapter_name=adapter.adapter_name,
        operation="book_room", payload=payload, ttl_seconds=1, store=store,
    )
    assert res2.status == "fresh"


def test_concurrent_call_safe(adapter, store, tmp_path):
    """50 parallele book_room-Calls (selber Payload) -> 1 fresh, 49 duplicate."""
    payload = {"hotel_id": "hildesheim", "room_type": "deluxe",
               "guest_email": "concurrent@x.de", "dates": ["2026-08-01", "2026-08-03"]}
    statuses: list[str] = []
    lock = threading.Lock()

    def worker():
        r = idempotency_check(
            tenant_id=payload["hotel_id"], adapter_name=adapter.adapter_name,
            operation="book_room", payload=payload, store=store,
        )
        with lock:
            statuses.append(r.status)

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert statuses.count("fresh") == 1
    assert statuses.count("duplicate") == 49
