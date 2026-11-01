import uuid
from dataclasses import dataclass, field
from typing import Any

import requests

DEFAULT_ITEMS = [{"sku": "SKU-100", "quantity": 2, "unitPriceCents": 1250}]


@dataclass
class CreateResult:
    status: int
    headers: dict
    body: Any

    @property
    def order_id(self) -> str | None:
        if isinstance(self.body, dict):
            return self.body.get("id")
        return None

    @property
    def replayed(self) -> bool:
        return self.headers.get("Idempotent-Replayed", "").lower() == "true"


@dataclass
class Api:
    base_url: str
    session: requests.Session = field(default_factory=requests.Session)
    timeout: float = 10.0

    @staticmethod
    def new_key() -> str:
        return "grader-" + uuid.uuid4().hex

    @staticmethod
    def body(customer: str = "cust-grader", items=None, currency: str = "USD") -> dict:
        return {"customerId": customer, "currency": currency, "items": items or DEFAULT_ITEMS}

    def create(self, key: str | None, body: dict | None = None) -> CreateResult:
        headers = {"Content-Type": "application/json"}
        if key is not None:
            headers["Idempotency-Key"] = key
        r = self.session.post(f"{self.base_url}/orders", json=body or self.body(),
                              headers=headers, timeout=self.timeout)
        try:
            parsed = r.json()
        except ValueError:
            parsed = r.text
        return CreateResult(r.status_code, dict(r.headers), parsed)

    def create_ok(self, key: str | None = None, body: dict | None = None) -> dict:
        """Create and assert 201. Returns the order body."""
        res = self.create(key or self.new_key(), body)
        assert res.status == 201, f"expected 201 creating order, got {res.status}: {res.body}"
        return res.body

    def get(self, order_id: str) -> requests.Response:
        return self.session.get(f"{self.base_url}/orders/{order_id}", timeout=self.timeout)

    def get_order(self, order_id: str) -> dict:
        r = self.get(order_id)
        assert r.status_code == 200, f"GET /orders/{order_id} -> {r.status_code}: {r.text}"
        return r.json()

    def history(self, order_id: str) -> list[dict]:
        r = self.session.get(f"{self.base_url}/orders/{order_id}/history", timeout=self.timeout)
        assert r.status_code == 200, f"GET /orders/{order_id}/history -> {r.status_code}: {r.text}"
        return r.json()

    def health(self) -> bool:
        try:
            r = self.session.get(f"{self.base_url}/actuator/health", timeout=3)
            return r.status_code == 200 and r.json().get("status") == "UP"
        except requests.RequestException:
            return False
