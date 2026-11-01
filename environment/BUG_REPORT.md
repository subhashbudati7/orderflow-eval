# ORD-2291: Duplicate orders, wrong status on dashboard, and stale reads after the Tuesday incident

Reporter: on-call (orders platform)
Severity: S2
Service: order-service 0.4.2
Environment: prod, reproduced in staging

## What happened

Tuesday 14:10 to 14:35 we had elevated latency on the Kafka cluster (broker 2
restart). During that window the storefront's create-order calls started timing
out at the gateway (5s) and retrying. Afterwards support got three threads of
complaints and the fulfillment dashboard looked wrong for a bunch of orders.

Three symptoms, all still reproducible in staging with the broker healthy, so
this is not "the incident did it". The incident just made it visible.

### 1. Retried requests sometimes create duplicate orders

Customer `cust-30217` has two orders with identical line items, 400ms apart,
same `Idempotency-Key` (`sf-9a1c0e7e-...`). The storefront logs show one
checkout and one gateway retry. Both got a `201`.

I can reproduce this in staging by firing ~20 identical `POST /orders` with the
same key at once (`hey -n 20 -c 20 ...`). I get anywhere from 3 to 15 orders.
Sequential retries are fine, it's only when they overlap.

We found 41 affected keys in prod for that window. Finance is going to ask.

### 2. Dashboard shows an older status than fulfillment has

Order `7f1c...` was PAID (1), SHIPPED (3), and then the warehouse's delayed
PICKING (2) event arrived about four seconds later. The order now says
`PICKING` with `lastEventSequence: 2`, history has all three rows, and the
carrier integration can't attach the tracking number because it checks for
`SHIPPED`.

WMS confirms their outbox worker was behind during the incident and replayed a
backlog, which is also why some orders have the same event twice in history
(`sequence` 2 appears twice on `a44e...`). ARCHITECTURE.md says we're supposed
to ignore anything at or below `last_event_sequence`; we clearly don't.

### 3. GET /orders/{id} keeps returning the old status

Even when the status update is applied correctly in Postgres, `GET /orders/{id}`
keeps returning the old status until the cache TTL expires (10 min). I checked
Redis directly: the key is still there after the consumer logs
`order ... -> SHIPPED (seq 3)`. The code has an eviction, so either it's not
firing or it's evicting the wrong key. The dashboard polls this endpoint, so
this is what the ops team actually sees.

## Steps to reproduce (staging / local compose)

1. `docker compose up -d --build` in `environment/`
2. Duplicates: send 20 concurrent `POST /orders` with the same
   `Idempotency-Key`, then `select count(*) from orders where idempotency_key = ...`.
3. Ordering: create an order, publish `PAID` seq 1, `SHIPPED` seq 3, then
   `PICKING` seq 2 (`tools/send_status.py`). Check `GET /orders/{id}` and
   `/history`.
4. Stale cache: `GET /orders/{id}` once (warms cache), publish a status event,
   `GET` again. Compare against `psql`.

## Expected

- One order per idempotency key, no matter how many concurrent retries. Retries
  get `200` with `Idempotent-Replayed: true` and the same order, exactly as
  documented in `docs/API.md`. The storefront handles that today; please don't
  change the response shape or status codes, the mobile team is mid-release.
- Status events applied in `sequence` order; late or duplicate events ignored
  and not recorded in history.
- `GET /orders/{id}` reflects a status change within a couple of seconds.
- Existing unit tests keep passing. Add tests for whatever you fix.

## Notes from the first look

- `OrderService.createOrder` does a find-then-save. I suspect that's the window.
- Publishing to Kafka happens inside the transaction, before the row is saved.
  Not sure if that's related to the duplicates or just a separate smell.
- The cache eviction in `OrderStatusService` has a `@CacheEvict` annotation that
  looks right to me, so I don't understand symptom 3.

Please keep the fix scoped to order-service. The fulfillment teams are not
going to change their producers this quarter.
