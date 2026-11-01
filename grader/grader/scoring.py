"""Scenario registry and scoring. No I/O in here so it can be unit tested.

Two kinds of scenario:

- "bug" scenarios fail on the shipped (buggy) code and must pass after a fix.
- "contract" scenarios pass on the shipped code and must keep passing. A fix
  that breaks one of these is a regression, and the task is failed even if
  every bug scenario is green.

A candidate PASSES when every scenario in both groups passes. The weighted
score exists for comparing partial attempts; it is not a pass/fail signal.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Scenario:
    id: str
    kind: str  # "bug" | "contract"
    weight: int
    title: str


SCENARIOS: dict[str, Scenario] = {s.id: s for s in [
    # duplicates
    Scenario("IDEM-01", "bug", 3, "concurrent retries with one key create exactly one order row"),
    Scenario("IDEM-02", "contract", 2, "sequential retry returns 200, Idempotent-Replayed: true, same id"),
    Scenario("IDEM-03", "contract", 1, "same key with a different body is 422 IDEMPOTENCY_KEY_REUSED"),
    Scenario("IDEM-04", "contract", 1, "missing Idempotency-Key is 400 MISSING_HEADER"),
    Scenario("IDEM-05", "bug", 2, "concurrent retries all get 2xx, exactly one 201, all the same id"),
    # ordering
    Scenario("ORD-01", "bug", 3, "a late event (lower sequence) does not overwrite the newer status"),
    Scenario("ORD-02", "bug", 2, "a late event is not recorded in history"),
    Scenario("ORD-03", "bug", 2, "a redelivered event (same sequence) appears once in history"),
    Scenario("ORD-04", "contract", 2, "CANCELLED after SHIPPED is applied (no state machine)"),
    Scenario("ORD-05", "contract", 1, "skipping states (PAID -> SHIPPED) is applied"),
    Scenario("ORD-06", "contract", 1, "an event for an unknown order does not stall the consumer"),
    # cache
    Scenario("CACHE-01", "bug", 3, "GET /orders/{id} reflects a status change within the documented window"),
    Scenario("CACHE-02", "contract", 1, "statusUpdatedAt is the event's occurredAt"),
    Scenario("CACHE-03", "contract", 1, "a replayed POST returns the order's current status"),
    # shape
    Scenario("API-01", "contract", 1, "order response has the documented fields and types"),
    Scenario("API-02", "contract", 1, "history is ordered by sequence with the documented fields"),
    # repository tests
    Scenario("UNIT-01", "contract", 2, "the repository's own unit tests pass (mvn test)"),
]}

BUG_IDS = [s.id for s in SCENARIOS.values() if s.kind == "bug"]
CONTRACT_IDS = [s.id for s in SCENARIOS.values() if s.kind == "contract"]


@dataclass
class Outcome:
    scenario: str
    passed: bool
    duration_s: float = 0.0
    detail: str = ""


@dataclass
class Summary:
    passed: bool
    score: float
    max_score: int
    bugs_fixed: list[str]
    bugs_remaining: list[str]
    regressions: list[str]
    missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "score": round(self.score, 3),
            "max_score": self.max_score,
            "bugs_fixed": self.bugs_fixed,
            "bugs_remaining": self.bugs_remaining,
            "regressions": self.regressions,
            "missing_scenarios": self.missing,
        }


def summarize(outcomes: list[Outcome]) -> Summary:
    by_id = {o.scenario: o for o in outcomes}
    unknown = [sid for sid in by_id if sid not in SCENARIOS]
    if unknown:
        raise ValueError(f"unknown scenario ids in results: {unknown}")

    missing = [sid for sid in SCENARIOS if sid not in by_id]
    # A scenario that never ran counts as failed. Silence is not a pass.
    for sid in missing:
        by_id[sid] = Outcome(sid, False, detail="did not run")

    bugs_fixed = [sid for sid in BUG_IDS if by_id[sid].passed]
    bugs_remaining = [sid for sid in BUG_IDS if not by_id[sid].passed]
    regressions = [sid for sid in CONTRACT_IDS if not by_id[sid].passed]

    max_score = sum(s.weight for s in SCENARIOS.values())
    score = sum(SCENARIOS[sid].weight for sid, o in by_id.items() if o.passed)

    return Summary(
        passed=not bugs_remaining and not regressions,
        score=score,
        max_score=max_score,
        bugs_fixed=bugs_fixed,
        bugs_remaining=bugs_remaining,
        regressions=regressions,
        missing=missing,
    )


def compare_to_expected(summary: Summary, expected: dict) -> list[str]:
    """Used by validate_grader.py. expected = {"passed": bool,
    "must_fail": [...ids], "must_pass": [...ids]}. Returns a list of
    mismatches; empty means the grader behaved as specified for this patch."""
    problems: list[str] = []
    if summary.passed != expected["passed"]:
        problems.append(f"overall passed={summary.passed}, expected {expected['passed']}")
    failing = set(summary.bugs_remaining) | set(summary.regressions)
    for sid in expected.get("must_fail", []):
        if sid not in failing:
            problems.append(f"{sid} passed but was expected to fail")
    for sid in expected.get("must_pass", []):
        if sid in failing:
            problems.append(f"{sid} failed but was expected to pass")
    return problems
