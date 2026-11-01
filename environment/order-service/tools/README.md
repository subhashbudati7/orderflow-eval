# tools

Small helpers for poking at a local stack. None of this ships in the image.

## send_status.py

Publishes one event to `order.status-updates`. Use it to replay what
fulfillment would send.

```
pip install confluent-kafka

ORDER=$(curl -s -X POST localhost:58080/orders \
  -H 'Idempotency-Key: demo-1' -H 'Content-Type: application/json' \
  -d '{"customerId":"c1","currency":"USD","items":[{"sku":"A","quantity":1,"unitPriceCents":500}]}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')

./tools/send_status.py $ORDER PAID 1 --source payments
./tools/send_status.py $ORDER SHIPPED 3 --source wms
./tools/send_status.py $ORDER PICKING 2 --source wms      # late arrival

curl -s localhost:58080/orders/$ORDER | python3 -m json.tool
curl -s localhost:58080/orders/$ORDER/history | python3 -m json.tool
```

## Watching the cache

```
docker compose exec redis redis-cli KEYS 'orderflow:*'
docker compose exec redis redis-cli GET "orderflow:orders::<order-id>"
```

## Poking the database

```
docker compose exec postgres psql -U orderflow -c 'select id, status, last_event_sequence, idempotency_key from orders;'
```
