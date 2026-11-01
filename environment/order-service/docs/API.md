# order-service HTTP API

Base path: `/orders`. All bodies are JSON. Timestamps are ISO-8601 in UTC.

Anything in this document is a contract. The storefront, the mobile app and
the fulfillment dashboard all code against it, so changes here need a version
bump and a heads-up in #orders-platform.

## POST /orders

Creates an order.

Headers

| Header            | Required | Notes |
|-------------------|----------|-------|
| `Idempotency-Key` | yes      | Client generated, max 128 chars. Clients reuse the same key when they retry. |
| `Content-Type`    | yes      | `application/json` |

Body

```json
{
  "customerId": "cust-8812",
  "currency": "USD",
  "items": [
    {"sku": "SKU-4471", "quantity": 2, "unitPriceCents": 1299}
  ]
}
```

Responses

| Status | When | Body / headers |
|--------|------|----------------|
| `201 Created` | first time this key is seen | Order object. `Location: /orders/{id}` |
| `200 OK` | same key, same body (a retry) | The **same** Order object as the original 201, plus header `Idempotent-Replayed: true` |
| `400 Bad Request` | header missing or body fails validation | `{"code": "MISSING_HEADER" \| "VALIDATION_FAILED", ...}` |
| `422 Unprocessable Entity` | same key, different body | `{"code": "IDEMPOTENCY_KEY_REUSED", ...}` |

Rules clients rely on:

- A given `Idempotency-Key` produces at most one order. Ever. Retries, parallel
  retries, retries after a timeout, all of them map to the one order.
- A replay is not an error. Clients treat `200` + `Idempotent-Replayed: true`
  as success and read the order id out of the body. Returning `409` or any
  4xx for a retry will cause the storefront to show the customer an error and
  let them "try again", which is exactly how we end up with double charges.
- The body of a replay is the order's current state. If a status update landed
  between the original request and the retry, the retry sees the newer status.
  Everything else in the body matches the original response.

## GET /orders/{id}

Returns the order. Served from the Redis cache when present (TTL 10 minutes),
otherwise from Postgres.

```json
{
  "id": "0b3f2a0e-5f4a-4a1e-9f3f-9cb1b1c5f0d2",
  "customerId": "cust-8812",
  "status": "SHIPPED",
  "totalCents": 2598,
  "currency": "USD",
  "lastEventSequence": 3,
  "statusUpdatedAt": "2026-03-01T10:14:07Z",
  "createdAt": "2026-03-01T10:02:51Z",
  "updatedAt": "2026-03-01T10:14:07.412Z"
}
```

Field notes:

- `status` is one of `CREATED`, `PAYMENT_PENDING`, `PAID`, `PICKING`,
  `SHIPPED`, `DELIVERED`, `CANCELLED`.
- `lastEventSequence` is the `sequence` of the most recent fulfillment event
  applied to this order. `0` means no event has been applied yet.
- `statusUpdatedAt` is when the current status happened according to the
  producer of the event (`occurredAt`), not when we processed it.
- The cache is expected to reflect a status change within a couple of seconds
  of the event being consumed. The fulfillment dashboard polls this endpoint
  every 2 seconds and shows whatever it gets.

`404` with `{"code": "ORDER_NOT_FOUND"}` for unknown ids.

## GET /orders/{id}/history

Every status event that was applied to the order, oldest first, ordered by
`sequence`.

```json
[
  {"status": "PAID",    "sequence": 1, "occurredAt": "...", "recordedAt": "...", "source": "payments"},
  {"status": "PICKING", "sequence": 2, "occurredAt": "...", "recordedAt": "...", "source": "wms"},
  {"status": "SHIPPED", "sequence": 3, "occurredAt": "...", "recordedAt": "...", "source": "wms"}
]
```

Rules:

- One entry per applied event. A redelivered event (same `sequence` for the
  same order) is applied once and appears once.
- Events that were not applied do not appear here. (Why would we not apply an
  event? See ARCHITECTURE.md, "Status updates".)

## GET /actuator/health

Standard Spring Boot health. Returns `{"status":"UP"}` when Postgres and Redis
are reachable. Kafka is not part of the health check; watch the consumer logs.
