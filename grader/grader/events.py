"""Publishes status events with the exact sequence numbers and timestamps a
scenario wants. The topic has one partition and the consumer runs with
concurrency 1, so the broker hands events to the service in the order we
produce them. That is what makes "late" and "duplicate" reproducible."""
import json
from datetime import datetime, timedelta, timezone

from confluent_kafka import Producer


def iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class StatusEvents:
    def __init__(self, bootstrap: str, topic: str):
        self.topic = topic
        self.producer = Producer({
            "bootstrap.servers": bootstrap,
            "acks": "all",
            "enable.idempotence": True,
            "linger.ms": 0,
        })
        # A fixed base time so occurredAt values are stable across runs.
        self.base_time = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)

    def occurred_at(self, sequence: int) -> str:
        """occurredAt grows with sequence, like a real producer's clock would."""
        return iso(self.base_time + timedelta(seconds=30 * sequence))

    def send(self, order_id: str, status: str, sequence: int,
             occurred_at: str | None = None, source: str = "grader") -> dict:
        event = {
            "orderId": order_id,
            "status": status,
            "sequence": sequence,
            "occurredAt": occurred_at or self.occurred_at(sequence),
            "source": source,
        }
        self.producer.produce(self.topic, key=order_id, value=json.dumps(event).encode())
        # Flush per event so ordering on the wire matches call order exactly.
        remaining = self.producer.flush(10)
        assert remaining == 0, "kafka producer did not flush"
        return event

    def send_many(self, order_id: str, steps: list[tuple[str, int]]) -> list[dict]:
        return [self.send(order_id, status, seq) for status, seq in steps]

    def close(self) -> None:
        self.producer.flush(5)
