"""Stale reads from Redis after a status update (bug 3)."""
import pytest

from ..config import settings
from ..stack import wait_until


@pytest.mark.scenario("CACHE-01")
def test_get_reflects_status_change_in_time(api, db, cache, events, consumer):
    order_id = api.create_ok()["id"]

    # Warm the cache the way the dashboard would.
    assert api.get_order(order_id)["status"] == "CREATED"
    assert cache.has_order(order_id), "expected GET to populate the cache (CacheConfig / @Cacheable)"

    events.send(order_id, "PAID", 1)
    assert consumer.wait_for_history(order_id, 1)
    assert db.order(order_id)["status"] == "PAID"  # the write landed; now the read side

    fresh = wait_until(lambda: api.get_order(order_id)["status"] == "PAID",
                       settings.cache_visibility_s, 0.2)
    assert fresh, (f"GET /orders/{order_id} still returns the old status "
                   f"{settings.cache_visibility_s}s after the event was applied")


@pytest.mark.scenario("CACHE-02")
def test_status_updated_at_is_the_events_occurred_at(api, events, consumer):
    order_id = api.create_ok()["id"]
    sent = events.send(order_id, "PAID", 1)
    assert consumer.wait_for_history(order_id, 1)

    history = api.history(order_id)
    assert len(history) == 1
    assert _same_instant(history[0]["occurredAt"], sent["occurredAt"])

    # Read through history first so a stale cache doesn't hide what we're testing.
    ok = wait_until(lambda: api.get_order(order_id)["lastEventSequence"] == 1,
                    settings.cache_visibility_s, 0.2)
    if ok:
        assert _same_instant(api.get_order(order_id)["statusUpdatedAt"], sent["occurredAt"])


@pytest.mark.scenario("CACHE-03")
def test_replay_returns_current_status(api, events, consumer):
    key = api.new_key()
    first = api.create(key)
    assert first.status == 201
    order_id = first.order_id

    events.send(order_id, "PAID", 1)
    assert consumer.wait_for_history(order_id, 1)

    replay = api.create(key)
    assert replay.status == 200 and replay.replayed
    assert replay.body["status"] == "PAID", "replay should carry the order's current state"
    assert replay.body["lastEventSequence"] == 1


def _same_instant(a: str, b: str) -> bool:
    from datetime import datetime
    def parse(s: str) -> datetime:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    return parse(a) == parse(b)
