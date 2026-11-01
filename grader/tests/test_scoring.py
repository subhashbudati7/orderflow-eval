"""Unit tests for the pure scoring code. No docker needed:

    cd grader && python -m pytest tests -q
"""
import json
from pathlib import Path

import pytest

from grader.scoring import BUG_IDS, CONTRACT_IDS, SCENARIOS, Outcome, compare_to_expected, summarize

EXPECTED_DIR = Path(__file__).resolve().parents[1] / "expected"


def outcomes(passing: set[str]) -> list[Outcome]:
    return [Outcome(sid, sid in passing) for sid in SCENARIOS]


def test_everything_passing_is_a_pass():
    s = summarize(outcomes(set(SCENARIOS)))
    assert s.passed
    assert s.score == s.max_score
    assert s.bugs_remaining == [] and s.regressions == []


def test_one_bug_left_is_a_fail():
    s = summarize(outcomes(set(SCENARIOS) - {"ORD-03"}))
    assert not s.passed
    assert s.bugs_remaining == ["ORD-03"]
    assert s.regressions == []


def test_one_regression_is_a_fail_even_with_all_bugs_fixed():
    s = summarize(outcomes(set(SCENARIOS) - {"ORD-04"}))
    assert not s.passed
    assert s.bugs_fixed == BUG_IDS
    assert s.regressions == ["ORD-04"]


def test_missing_scenario_counts_as_failed():
    partial = [Outcome(sid, True) for sid in SCENARIOS if sid != "UNIT-01"]
    s = summarize(partial)
    assert not s.passed
    assert s.missing == ["UNIT-01"]
    assert "UNIT-01" in s.regressions


def test_unknown_scenario_id_is_an_error():
    with pytest.raises(ValueError):
        summarize([Outcome("NOPE-99", True)])


def test_baseline_shape_matches_registry():
    """The baseline expectation file must list every bug as must_fail and every
    contract scenario as must_pass. If someone adds a scenario and forgets
    the expected file, this catches it."""
    baseline = json.loads((EXPECTED_DIR / "00-baseline.json").read_text())["expected"]
    assert sorted(baseline["must_fail"]) == sorted(BUG_IDS)
    assert sorted(baseline["must_pass"]) == sorted(CONTRACT_IDS)


@pytest.mark.parametrize("path", sorted(EXPECTED_DIR.glob("*.json")), ids=lambda p: p.stem)
def test_expected_files_reference_known_scenarios(path):
    exp = json.loads(path.read_text())["expected"]
    for sid in exp["must_fail"] + exp["must_pass"]:
        assert sid in SCENARIOS, f"{path.name} references unknown scenario {sid}"
    assert not set(exp["must_fail"]) & set(exp["must_pass"])
    if exp["passed"]:
        assert exp["must_fail"] == []


def test_compare_to_expected_reports_mismatches():
    s = summarize(outcomes(set(SCENARIOS) - {"IDEM-01"}))
    problems = compare_to_expected(s, {"passed": True, "must_pass": ["IDEM-01"], "must_fail": ["ORD-01"]})
    assert any("passed=False" in p for p in problems)
    assert any("IDEM-01 failed" in p for p in problems)
    assert any("ORD-01 passed" in p for p in problems)


def test_compare_to_expected_is_quiet_when_it_matches():
    s = summarize(outcomes(set(SCENARIOS) - {"IDEM-01"}))
    assert compare_to_expected(s, {"passed": False, "must_fail": ["IDEM-01"], "must_pass": ["ORD-01"]}) == []


def test_weights_are_positive_and_bugs_outweigh_shape_checks():
    assert all(s.weight > 0 for s in SCENARIOS.values())
    assert SCENARIOS["IDEM-01"].weight > SCENARIOS["API-01"].weight
