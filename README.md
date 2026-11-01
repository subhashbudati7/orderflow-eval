# orderflow-eval

A debugging task for coding agents, built around a small Java order service
with four bugs that interact, plus a Python grader that decides whether a
fix is actually a fix.

I built this because most coding-agent benchmarks I've looked at grade single
file changes against unit tests. The bugs I've spent real time on at work
looked nothing like that: a retry storm creating duplicate rows, a Kafka
consumer applying a stale event over a fresh one, Redis handing back a value
Postgres stopped agreeing with ten minutes ago. Fixing one of those often
breaks a contract some other team relies on. I wanted an environment where an
agent has to deal with all of that at once and a grader that can tell the
difference between "the symptom went away" and "the system is correct".

## What's in the box

```
environment/            what the agent gets
  BUG_REPORT.md         ticket ORD-2291, written the way on-call would write it
  docker-compose.yml    Postgres 16, Redis 7, Kafka 3.8 (KRaft), the service
  order-service/        Spring Boot 3.5 / Java 21, Flyway, Spring Kafka, Spring Cache on Redis
    docs/API.md         the HTTP contract the fix must preserve
    docs/ARCHITECTURE.md  what the Kafka topics promise and what the consumer should do
    tools/              send_status.py for publishing events by hand

grader/                 Python, pytest, confluent-kafka, psycopg, redis
  run_grader.py         grade one tree (optionally with a patch applied)
  validate_grader.py    grade every patch in patches/ and check the grader's verdicts
  grader/scenarios/     16 scenarios across idempotency, ordering, cache, API shape
  expected/             what each patch must pass and fail

patches/
  reference.patch       the fix I'd merge
  alt-fix.patch         a second correct fix with different mechanics
  incomplete/           five plausible wrong fixes, each pinned to the scenarios it must fail

tasks/                  the task spec an agent harness reads
results/                attempt write-ups, grader runs, findings
```

## The bugs

All four are in `order-service` and all four are reachable from the one bug
report. They're described from the fix side in `patches/README.md`; from the
symptom side in `environment/BUG_REPORT.md`. Short version:

1. `POST /orders` is find-then-insert with no unique index, and a synchronous
   Kafka publish sits in the gap. Concurrent retries with the same
   `Idempotency-Key` make several orders.
2. The status consumer applies whatever arrives. A delayed `PICKING (seq 2)`
   overwrites `SHIPPED (seq 3)`. Redeliveries get recorded twice.
3. The cache eviction after a status update is a `@CacheEvict` on a method
   called through `this`, so Spring's proxy never sees it. Redis serves the
   old status until the TTL expires.
4. Two fixes that look right break the documented contract: answering `409`
   to a retry (clients expect `200` + `Idempotent-Replayed: true`), and
   enforcing a status state machine (`CANCELLED` after `SHIPPED` is valid).

The bug report nudges toward the right places without saying what's wrong.
It also includes a red herring the first on-call wrote down (the publish
inside the transaction), which is a real smell but not the cause of any of the
three symptoms.

## Running it

You need Docker with compose, Python 3.11+, and either Maven or a willingness
to let the grader run Maven in a container.

```
cd grader
pip install -r requirements.txt

python run_grader.py                                      # shipped code: FAIL, 6 bug scenarios red
python run_grader.py --patch ../patches/reference.patch   # PASS
python validate_grader.py                                 # all 8 expected outcomes, ~20 min
```

To grade an agent's attempt, point `--source` at the agent's copy of
`environment/` and give it a label:

```
python run_grader.py --source ~/runs/sonnet-3/environment --label sonnet-3
```

Then fill in `results/attempts/TEMPLATE.md`.

## How grading works

Scenarios are split into bug scenarios (fail on the shipped code, must pass
after a fix) and contract scenarios (pass on the shipped code, must keep
passing). A candidate passes only if both sets are green. There is a weighted
score for comparing partial attempts but it never decides pass/fail; one
regression is a fail no matter how many bugs got fixed.

Everything the grader asserts about ordering is read from Postgres, not from
the (possibly stale) HTTP endpoint, so the cache bug can't disguise an
ordering result. The grader never sleeps a fixed amount to let the consumer
catch up; it waits on history (uncached) or on a canary event through the
single-partition topic. `grader/README.md` goes through each scenario and
the reasoning.

The grader is itself tested: `validate_grader.py` runs it against the shipped
code, both correct patches and all five incomplete ones, and checks every
verdict against `grader/expected/`. If a scenario starts failing on
`reference.patch`, the scenario is wrong.

## What I'd do next

- A scenario that catches evict-before-commit (needs a controllable delay on
  the Postgres side; toxiproxy is the obvious tool).
- Pin the original unit test methods so an agent can't pass `UNIT-01` by
  deleting tests.
- A second task on the same service: the `OrderCreated` publish is not
  transactional with the insert, so a rollback leaves a ghost event. That one
  needs failure injection to grade.
- Run actual agents and write up what they do. `results/attempts/` is empty
  on purpose until there are real numbers.

## Status

- [x] environment: service, compose stack, docs, bug report
- [x] grader: 16 scenarios, runner, validation harness, scoring unit tests
- [x] patches: reference, alternative, five incomplete, expected outcomes
- [ ] `make validate` green on a machine with Docker (record the run folder here)
- [ ] first agent attempts written up in `results/attempts/`
