"""Duplicate orders on retry (bug 1) and the replay contract around it."""
from concurrent.futures import ThreadPoolExecutor

import pytest

from ..api import Api
from ..config import settings


def fire_concurrent(api: Api, key: str, n: int):
    body = api.body()
    # Each thread gets its own Session; sharing one would serialize on the pool.
    def one(_):
        return Api(api.base_url).create(key, body)
    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(one, range(n)))


@pytest.mark.scenario("IDEM-01")
def test_concurrent_retries_create_one_row(api, db):
    key = api.new_key()
    results = fire_concurrent(api, key, settings.concurrency)

    # Only the row count matters here. What the responses looked like is IDEM-05,
    # so a fix that stops the duplicates but answers 409 still gets credit for this one.
    assert any(r.status == 201 for r in results), "no request succeeded at all"
    rows = db.count_orders_for_key(key)
    assert rows == 1, f"{rows} order rows for one idempotency key"


@pytest.mark.scenario("IDEM-05")
def test_concurrent_retries_follow_replay_contract(api, db):
    key = api.new_key()
    results = fire_concurrent(api, key, settings.concurrency)

    statuses = sorted(r.status for r in results)
    assert all(s in (200, 201) for s in statuses), f"statuses: {statuses}"
    assert statuses.count(201) == 1, f"expected exactly one 201, got {statuses.count(201)}"

    ids = {r.order_id for r in results}
    assert len(ids) == 1, f"responses disagree on the order id: {ids}"

    for r in results:
        if r.status == 200:
            assert r.replayed, "200 without Idempotent-Replayed: true"
        else:
            assert not r.replayed, "201 must not carry Idempotent-Replayed"


@pytest.mark.scenario("IDEM-02")
def test_sequential_retry_is_replayed(api):
    key = api.new_key()
    first = api.create(key)
    second = api.create(key)

    assert first.status == 201
    assert second.status == 200, f"retry returned {second.status}: {second.body}"
    assert second.replayed
    assert second.order_id == first.order_id
    for field in ("customerId", "totalCents", "currency", "createdAt"):
        assert second.body[field] == first.body[field], field


@pytest.mark.scenario("IDEM-03")
def test_key_reuse_with_different_body_is_422(api):
    key = api.new_key()
    assert api.create(key).status == 201
    other = api.create(key, api.body(items=[{"sku": "SKU-100", "quantity": 9, "unitPriceCents": 1250}]))

    assert other.status == 422
    assert other.body["code"] == "IDEMPOTENCY_KEY_REUSED"


@pytest.mark.scenario("IDEM-04")
def test_missing_key_is_400(api):
    res = api.create(None)
    assert res.status == 400
    assert res.body["code"] == "MISSING_HEADER"
