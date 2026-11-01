#!/usr/bin/env python3
"""Publish a status event to order.status-updates on the local compose stack.

Examples:

    ./tools/send_status.py <order-id> PAID 1
    ./tools/send_status.py <order-id> SHIPPED 3 --source wms
    ./tools/send_status.py <order-id> PICKING 2 --occurred-at 2026-03-01T10:05:00Z

Requires: pip install confluent-kafka
"""
import argparse
import json
import sys
from datetime import datetime, timezone

try:
    from confluent_kafka import Producer
except ImportError:  # pragma: no cover
    sys.exit("confluent-kafka not installed. pip install confluent-kafka")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("order_id")
    p.add_argument("status")
    p.add_argument("sequence", type=int)
    p.add_argument("--source", default="manual")
    p.add_argument("--occurred-at", default=None, help="ISO-8601 UTC, defaults to now")
    p.add_argument("--bootstrap", default="localhost:59094")
    p.add_argument("--topic", default="order.status-updates")
    args = p.parse_args()

    occurred = args.occurred_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    event = {
        "orderId": args.order_id,
        "status": args.status,
        "sequence": args.sequence,
        "occurredAt": occurred,
        "source": args.source,
    }

    producer = Producer({"bootstrap.servers": args.bootstrap})
    producer.produce(args.topic, key=args.order_id, value=json.dumps(event).encode())
    producer.flush(10)
    print(json.dumps(event))


if __name__ == "__main__":
    main()
