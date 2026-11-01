"""Response shapes from docs/API.md. These pass on the shipped code; a fix
that changes the wire format fails them."""
from datetime import datetime

import pytest

ORDER_FIELDS = {
    "id": str,
    "customerId": str,
    "status": str,
    "totalCents": int,
    "currency": str,
    "lastEventSequence": int,
    "statusUpdatedAt": str,
    "createdAt": str,
    "updatedAt": str,
}

HISTORY_FIELDS = {"status": str, "sequence": int, "occurredAt": str, "recordedAt": str, "source": str}

STATUSES = {"CREATED", "PAYMENT_PENDING", "PAID", "PICKING", "SHIPPED", "DELIVERED", "CANCELLED"}


def _check_fields(obj: dict, spec: dict[str, type]) -> None:
    missing = spec.keys() - obj.keys()
    assert not missing, f"missing fields {sorted(missing)} in {obj}"
    for name, typ in spec.items():
        assert isinstance(obj[name], typ), f"{name} should be {typ.__name__}, got {obj[name]!r}"


def _is_iso(s: str) -> bool:
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


@pytest.mark.scenario("API-01")
def test_order_response_shape(api):
    key = api.new_key()
    created = api.create(key, api.body(customer="cust-42",
                                        items=[{"sku": "A", "quantity": 3, "unitPriceCents": 700},
                                               {"sku": "B", "quantity": 1, "unitPriceCents": 50}]))
    assert created.status == 201
    assert created.headers.get("Location") == f"/orders/{created.order_id}"

    body = created.body
    _check_fields(body, ORDER_FIELDS)
    assert body["status"] in STATUSES
    assert body["status"] == "CREATED"
    assert body["lastEventSequence"] == 0
    assert body["totalCents"] == 3 * 700 + 50
    assert body["currency"] == "USD"
    assert body["customerId"] == "cust-42"
    for ts in ("statusUpdatedAt", "createdAt", "updatedAt"):
        assert _is_iso(body[ts]), ts

    fetched = api.get_order(body["id"])
    _check_fields(fetched, ORDER_FIELDS)
    assert fetched["id"] == body["id"]

    missing = api.get("00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
    assert missing.json()["code"] == "ORDER_NOT_FOUND"


@pytest.mark.scenario("API-02")
def test_history_shape_and_order(api, events, consumer):
    order_id = api.create_ok()["id"]
    events.send(order_id, "PAID", 1, source="payments")
    events.send(order_id, "PICKING", 2, source="wms")
    assert consumer.wait_for_history(order_id, 2)

    history = api.history(order_id)
    assert len(history) == 2
    for entry in history:
        _check_fields(entry, HISTORY_FIELDS)
        assert entry["status"] in STATUSES
        assert _is_iso(entry["occurredAt"]) and _is_iso(entry["recordedAt"])
    assert [h["sequence"] for h in history] == [1, 2]
    assert [h["source"] for h in history] == ["payments", "wms"]

    assert api.session.get(f"{api.base_url}/orders/00000000-0000-0000-0000-000000000000/history").status_code == 404
