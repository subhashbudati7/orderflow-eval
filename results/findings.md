# Findings

Running notes across attempts. Newest at the top within each section.

## Agent failure modes

(none recorded yet; first attempts pending)

## Grader

- Decided to assert ordering scenarios against Postgres rather than
  `GET /orders/{id}`. The cache bug would otherwise make ORD-01 fail for the
  wrong reason and an agent that fixed ordering but not caching would get no
  credit for it.
- `IDEM-01` used to assert every response was 2xx. Moved that to `IDEM-05` so
  the 409 patch gets credit for stopping the duplicate rows while still failing
  the contract check. Two scenarios, two facts.
- Ordering scenarios use a canary event on a throwaway order instead of a
  fixed sleep after the late event. Topic has one partition and the listener
  has concurrency 1, so once the canary is in history everything before it has
  been consumed. A sleep would have been a guess about consumer latency.

## Open questions

- CACHE-01 only checks that the cache catches up within 5 seconds. A fix that
  evicts inside the transaction (patches/incomplete/04-cache-only) passes even
  though it has a real race. Catching that needs a scenario that pins a GET
  between the eviction and the commit, which means hooking the service
  (a debug endpoint or a toxiproxy delay on Postgres). Not done yet.
- The unit-test scenario (UNIT-01) runs whatever tests exist after the agent's
  changes. An agent can delete tests. Worth adding a check that the original
  test methods still exist, or keeping a grader-owned copy of the contract
  tests and compiling them against the agent's tree.
