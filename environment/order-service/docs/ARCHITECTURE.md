# order-service architecture

order-service owns the `orders` table and is the only writer to it. It takes
orders from the storefront over HTTP, tells the rest of the platform about them
over Kafka, and listens for status changes coming back from fulfillment.

```
 storefront ──POST /orders──▶ order-service ──▶ Postgres (orders, order_status_history)
                                   │   ▲             ▲
                                   │   │             │ cache miss
                                   │   │        Redis (orders cache, 10m TTL)
                                   │   │
          order.events  ◀──────────┘   └────────── order.status-updates
          (OrderCreated)                           (from payments / wms / carrier)
```

## Components

`api/` is the HTTP layer. `OrderController` maps to `OrderService` for writes
and `OrderQueryService` for reads.

`service/OrderService.createOrder` handles idempotent creation. It computes a
fingerprint of the request body, looks up the idempotency key, and either
replays the existing order or creates a new one. New orders are announced on
`order.events` before the request returns.

`service/OrderQueryService.getOrder` is `@Cacheable("orders")`. The cache is
Redis, configured in `config/CacheConfig`, key is the order id, TTL 10 minutes.
`getHistory` is never cached.

`messaging/OrderStatusConsumer` is the Kafka listener for
`order.status-updates`. It hands each event to
`service/OrderStatusService.applyStatusUpdate`, which updates the row, appends
to `order_status_history`, and drops the cached copy of the order.

## Status updates

Fulfillment is three systems (payments, the warehouse system, the carrier
integration) and they all publish to the same topic. Facts about that topic:

- Each event carries `sequence`, a per-order counter that fulfillment increments
  for every transition it emits. It is strictly increasing per order on the
  producer side.
- Delivery is at least once. The same event can show up twice, usually after a
  consumer group rebalance.
- Delivery is not in order across producers. Payments and the warehouse system
  publish from different services, and we have seen a `PICKING` (seq 2) arrive
  a few seconds after `SHIPPED` (seq 3) when the warehouse's outbox worker was
  behind.

What the order service is supposed to do with that:

- Apply an event if and only if its `sequence` is greater than the order's
  `last_event_sequence`. Anything else is a redelivery or a late arrival, log
  it and move on. Do not treat it as an error; the consumer must keep going.
- There is deliberately no state machine here. Cancellation can come from any
  state up to and including `SHIPPED` (customer refused delivery), and some
  flows skip states (`PAID` straight to `SHIPPED` for digital goods). Ordering
  is by `sequence`, full stop.
- `statusUpdatedAt` is the producer's `occurredAt`, so the dashboard shows when
  something happened, not when we got around to processing it.

## Caching

`GET /orders/{id}` is the hottest endpoint we have (the dashboard polls it).
Reads go through Spring's cache abstraction backed by Redis. Writes to the
order (status updates) are responsible for invalidating the cached entry. The
TTL is a safety net, not the invalidation strategy; 10 minutes of stale status
on the dashboard is not acceptable.

## Transactions

Service methods are `@Transactional`. Keep in mind that Kafka is not part of
the database transaction. Whatever we publish is published whether or not the
transaction commits.

## Running locally

```
docker compose up -d --build        # from the environment/ directory
curl -s localhost:58080/actuator/health
```

`tools/send_status.py` publishes a status event to the local broker so you can
poke at the consumer without the real fulfillment systems. `tools/README.md`
has examples.

Ports are remapped (58080, 55432, 56379, 59094) so this stack can run next to
whatever else you have on the usual ports.
