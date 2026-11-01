"""Out-of-order and redelivered status events (bug 2) and the rules in
ARCHITECTURE.md that a fix must not break.

Status assertions here read Postgres directly. GET /orders/{id} is cached and
the cache has its own bug (CACHE-01); mixing the two would make it impossible
to tell which one an agent fixed."""
import uuid

import pytest


@pytest.mark.scenario("ORD-01")
def test_late_event_does_not_overwrite_newer_status(api, db, events, consumer):
    order_id = api.create_ok()["id"]
    events.send_many(order_id, [("PAID", 1), ("SHIPPED", 3)])
    assert consumer.wait_for_history(order_id, 3)

    events.send(order_id, "PICKING", 2)  # the warehouse's late event
    consumer.barrier()

    row = db.order(order_id)
    assert row["status"] == "SHIPPED", f"late PICKING overwrote SHIPPED: {row}"
    assert row["lastEventSequence"] == 3, row


@pytest.mark.scenario("ORD-02")
def test_late_event_is_not_recorded_in_history(api, db, events, consumer):
    order_id = api.create_ok()["id"]
    events.send_many(order_id, [("PAID", 1), ("SHIPPED", 3)])
    assert consumer.wait_for_history(order_id, 3)

    events.send(order_id, "PICKING", 2)
    consumer.barrier()

    seqs = db.history_sequences(order_id)
    assert seqs == [1, 3], f"history should hold only applied events, got {seqs}"
    assert [h["sequence"] for h in api.history(order_id)] == [1, 3]


@pytest.mark.scenario("ORD-03")
def test_redelivered_event_is_applied_once(api, db, events, consumer):
    order_id = api.create_ok()["id"]
    events.send_many(order_id, [("PAID", 1), ("PICKING", 2)])
    assert consumer.wait_for_history(order_id, 2)

    events.send(order_id, "PICKING", 2)  # rebalance replay
    consumer.barrier()

    seqs = db.history_sequences(order_id)
    assert seqs == [1, 2], f"duplicate delivery produced {seqs}"
    row = db.order(order_id)
    assert row["status"] == "PICKING" and row["lastEventSequence"] == 2


@pytest.mark.scenario("ORD-04")
def test_cancel_after_shipped_is_applied(api, db, events, consumer):
    order_id = api.create_ok()["id"]
    events.send_many(order_id, [("PAID", 1), ("PICKING", 2), ("SHIPPED", 3), ("CANCELLED", 4)])
    assert consumer.wait_for_history(order_id, 4), \
        "CANCELLED (seq 4) after SHIPPED was never applied; ARCHITECTURE.md forbids a state machine here"

    row = db.order(order_id)
    assert row["status"] == "CANCELLED"
    assert row["lastEventSequence"] == 4


@pytest.mark.scenario("ORD-05")
def test_skipping_states_is_applied(api, db, events, consumer):
    order_id = api.create_ok()["id"]
    events.send_many(order_id, [("PAID", 1), ("SHIPPED", 2)])
    assert consumer.wait_for_history(order_id, 2), "PAID -> SHIPPED (digital goods flow) was not applied"

    assert db.order(order_id)["status"] == "SHIPPED"


@pytest.mark.scenario("ORD-06")
def test_unknown_order_does_not_stall_consumer(api, db, events, consumer):
    ghost = str(uuid.uuid4())
    events.send(ghost, "PAID", 1)

    order_id = api.create_ok()["id"]
    events.send(order_id, "PAID", 1)
    assert consumer.wait_for_history(order_id, 1), \
        "consumer stopped applying events after one for an unknown order"
