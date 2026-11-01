# grader

Python harness that grades a candidate `environment/` tree. It copies the
tree, applies an optional patch, runs the repo's unit tests, brings the stack
up with docker compose, drives it through 16 scenarios over HTTP, Kafka,
Postgres and Redis, and writes a report.

## Requirements

- Docker with the compose plugin
- Python 3.11+
- `pip install -r requirements.txt` (requests, confluent-kafka, psycopg, redis, pytest)
- Maven, or Docker will be used to run the unit tests in a `maven:3.9` image

## Usage

```
cd grader
pip install -r requirements.txt

python run_grader.py                                       # shipped code, should FAIL
python run_grader.py --patch ../patches/reference.patch    # should PASS
python run_grader.py --source /path/to/agent/environment --label sonnet-attempt-3

python validate_grader.py            # every case in expected/
python validate_grader.py --repeat 3 # flakiness check

python -m pytest tests -q            # unit tests for the scoring code, no docker
```

Each run writes `results/runs/<timestamp>-<label>/` with `report.json`,
`summary.md`, `pytest.log`, `mvn-test.log`, and the raw `scenarios.json`.

Exit code is 0 when the candidate passes, 1 otherwise (`--exit-zero` to
suppress, which `validate_grader.py` uses).

## Scenarios

Defined in `grader/scoring.py`. Two kinds:

- bug: fails on the shipped code, must pass after a fix. `IDEM-01`, `IDEM-05`,
  `ORD-01`, `ORD-02`, `ORD-03`, `CACHE-01`.
- contract: passes on the shipped code, must keep passing. Everything else,
  including `UNIT-01` (the repository's own `mvn test`).

A candidate passes only if all bug scenarios pass and no contract scenario
fails. The weighted score in the report is for comparing partial attempts and
is not used for pass/fail.

| id | checks |
|---|---|
| IDEM-01 | 24 concurrent `POST /orders` with one key leave exactly one row in `orders` |
| IDEM-05 | those 24 responses: all 2xx, exactly one `201`, all the same id, `200`s carry `Idempotent-Replayed: true` |
| IDEM-02 | sequential retry: `200`, header, same id and body |
| IDEM-03 | same key, different body: `422 IDEMPOTENCY_KEY_REUSED` |
| IDEM-04 | no key: `400 MISSING_HEADER` |
| ORD-01 | PAID(1), SHIPPED(3), then late PICKING(2): row stays SHIPPED / seq 3 |
| ORD-02 | same sequence of events: history is `[1, 3]` |
| ORD-03 | PICKING(2) delivered twice: history is `[1, 2]` |
| ORD-04 | SHIPPED(3) then CANCELLED(4) applies |
| ORD-05 | PAID(1) then SHIPPED(2) applies |
| ORD-06 | an event for an unknown order id doesn't stop later events |
| CACHE-01 | GET warms cache, event applied, GET shows new status within 5s |
| CACHE-02 | `statusUpdatedAt` equals the event's `occurredAt` |
| CACHE-03 | a replayed POST returns the current status |
| API-01 | order response fields, types, `Location`, 404 shape |
| API-02 | history fields, ordering, 404 |
| UNIT-01 | `mvn -q test` exits 0 |

## How the scenarios stay reproducible

Concurrency: `IDEM-01/05` use a thread pool of 24 (`GRADER_CONCURRENCY`), one
`requests.Session` per thread. The shipped code does a find, then a synchronous
Kafka publish (network round trip, broker ack), then the insert, so the window
between check and write is tens of milliseconds wide and 24 overlapping
requests land in it reliably. If IDEM-01 ever passes on the shipped code, raise
the concurrency before suspecting anything else.

Event ordering: the topic has one partition and the listener container has
concurrency 1, so the service sees events in exactly the order the grader
produces them. The producer flushes after every event.

Waiting: scenarios never `sleep` for a fixed time to let the consumer catch
up. They poll `GET /orders/{id}/history` (never cached) for the sequence they
just sent, or use `Consumer.barrier()`, which sends a canary event on a fresh
order and waits for it to show up. Anything produced before the canary has
been consumed by then. The one timed wait is `CACHE-01`, where the timeout
*is* the contract ("within a couple of seconds", budgeted as 5).

State: every scenario starts with `TRUNCATE orders, order_status_history` and
`FLUSHALL`. Events left on the topic from a previous scenario are for order ids
that no longer exist and are dropped by the consumer.

Source of truth: ordering scenarios read Postgres directly so the cache bug
cannot mask or fake an ordering result. Cache scenarios go through the API.

## What it does not catch

- Evicting the cache inside the transaction rather than after commit. The
  race window is a few milliseconds and CACHE-01 only checks eventual
  visibility. `patches/incomplete/04-cache-only.patch` passes for this reason.
  Noted in `results/findings.md`.
- A candidate that deletes unit tests. `UNIT-01` runs whatever is there.
- Kafka publish happening before the DB commit. Not observable from outside
  without failure injection.

## Environment variables

| var | default | meaning |
|---|---|---|
| `GRADER_BASE_URL` | `http://localhost:58080` | service |
| `GRADER_KAFKA` | `localhost:59094` | broker external listener |
| `GRADER_PG_DSN` | `postgresql://orderflow:orderflow@localhost:55432/orderflow` | |
| `GRADER_REDIS_URL` | `redis://localhost:56379/0` | |
| `GRADER_MANAGE_STACK` | `1` | `0` to grade an already-running stack |
| `GRADER_COMPOSE_DIR` | `environment/` | set by `run_grader.py` to the prepared copy |
| `GRADER_CONCURRENCY` | `24` | threads for IDEM-01/05 |
| `GRADER_CONSUMER_TIMEOUT` | `15` | seconds to wait for the consumer |
| `GRADER_CACHE_VISIBILITY` | `5` | seconds allowed for CACHE-01 |
