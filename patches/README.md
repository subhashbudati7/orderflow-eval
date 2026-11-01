# patches

Git diffs against `environment/order-service`. Apply with
`git apply <patch>` from inside that directory, or let the grader do it:

```
cd grader && python run_grader.py --patch ../patches/reference.patch
```

These exist to validate the grader, not to hand to agents. If a scenario fails
on `reference.patch` the scenario is wrong, not the patch.

## reference.patch

The fix I'd actually merge.

Duplicates: V2 migration makes `idempotency_key` unique. `createOrder` drops
`@Transactional` so the repository `save` runs in its own short transaction;
a `DataIntegrityViolationException` means another retry won, so we re-read
that row and return it as a replay. Publishing to Kafka moves after the save,
so nothing is announced for a row that didn't commit.

Ordering: `applyStatusUpdate` returns early when `event.sequence <=
order.lastEventSequence`. Late arrivals and redeliveries are logged and
skipped, never written to history.

Cache: the `@CacheEvict` on `evictCachedOrder` never did anything because the
method was called through `this`, bypassing the Spring proxy. Replaced with a
direct `CacheManager` eviction registered in `afterCommit`, so a concurrent
GET can't re-cache the pre-commit row.

Tests: adds cases for the late event, the redelivery, cancel-after-shipped,
eviction, the lost insert race, and save-before-publish ordering.

## alt-fix.patch

Same behaviour, different mechanics, to make sure the grader scores outcomes
rather than one particular implementation.

Duplicates: `pg_advisory_xact_lock(hashtext(key))` at the top of the
(still transactional) `createOrder`, so concurrent creates for one key queue
rather than race. Unique constraint added as a backstop. Kafka publish goes
through a `TransactionSynchronization.afterCommit`.

Ordering: a single conditional JPQL `UPDATE ... WHERE last_event_sequence <
:sequence`. Zero rows updated means late or duplicate.

Cache: write-through instead of evict. `OrderStatusService` publishes an
in-process `OrderStatusApplied` event; `OrderCacheRefresher` handles it with
`@TransactionalEventListener(AFTER_COMMIT)`, reloads the row and `put`s the
fresh `OrderResponse`.

## incomplete/

Each one is a fix a reasonable engineer could ship after reading the bug
report too quickly. `grader/expected/*.json` records exactly which scenarios
each must fail.

| patch | what it does | what the grader should say |
|---|---|---|
| `01-unique-index-409` | unique index, returns `409` when the insert collides | duplicates gone (IDEM-01 passes) but IDEM-05 fails: the replay contract says `200` + `Idempotent-Replayed`. Ordering and cache untouched. |
| `02-ordering-only` | the `<=` sequence guard, nothing else | ORD-* pass, IDEM-01/05 and CACHE-01 still fail |
| `03-state-machine` | reference fix for duplicates and cache, but ordering via an allowed-transitions table | all bug scenarios pass; ORD-04 fails because `SHIPPED -> CANCELLED` is rejected. This is the "plausible fix that breaks the contract" case. |
| `04-cache-only` | swaps the self-invoked `@CacheEvict` for a direct `CacheManager` call inside the transaction | CACHE-01 passes, everything else still broken. (The evict-before-commit race is real but not graded; see grader/README.md.) |
| `05-off-by-one` | reference fix with `<` instead of `<=` | only ORD-03 fails: a redelivered event gets applied twice |
