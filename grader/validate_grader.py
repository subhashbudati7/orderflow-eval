#!/usr/bin/env python3
"""Check that the grader itself behaves: the buggy code fails the bug
scenarios and nothing else, both correct patches pass everything, and each
deliberately incomplete patch fails exactly the scenarios it should.

    python validate_grader.py            # all cases in expected/
    python validate_grader.py reference  # one case
    python validate_grader.py --repeat 3 # run each case 3x to catch flakiness

Every case is a full grader run (compose up, scenarios, compose down), so this
takes a while. Budget roughly 2 to 3 minutes per case.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from grader.config import ROOT  # noqa: E402
from grader.scoring import Outcome, compare_to_expected, summarize  # noqa: E402

EXPECTED_DIR = HERE / "expected"
RUNS_DIR = ROOT / "results" / "runs"


def load_cases(names: list[str]) -> list[dict]:
    files = sorted(EXPECTED_DIR.glob("*.json"))
    if names:
        files = [f for f in files if f.stem in names]
        missing = set(names) - {f.stem for f in files}
        if missing:
            raise SystemExit(f"no expected file for: {sorted(missing)}")
    return [dict(json.loads(f.read_text()), name=f.stem) for f in files]


def newest_report(label: str) -> dict:
    candidates = sorted(RUNS_DIR.glob(f"*-{label}"))
    if not candidates:
        raise SystemExit(f"no run folder for {label}")
    return json.loads((candidates[-1] / "report.json").read_text())


def run_case(case: dict, attempt: int) -> list[str]:
    label = f"validate-{case['name']}-{attempt}"
    cmd = [sys.executable, str(HERE / "run_grader.py"), "--label", label, "--exit-zero"]
    if case.get("patch"):
        cmd += ["--patch", str(ROOT / case["patch"])]
    print(f"\n=== {case['name']} (attempt {attempt}) ===", flush=True)
    subprocess.run(cmd, check=False)

    report = newest_report(label)
    outcomes = [Outcome(**{k: s[k] for k in ("scenario", "passed", "duration_s", "detail")})
                for s in report["scenarios"]]
    return compare_to_expected(summarize(outcomes), case["expected"])


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("names", nargs="*")
    p.add_argument("--repeat", type=int, default=1)
    args = p.parse_args()

    cases = load_cases(args.names)
    failures: dict[str, list[str]] = {}
    for case in cases:
        for attempt in range(1, args.repeat + 1):
            problems = run_case(case, attempt)
            if problems:
                failures.setdefault(case["name"], []).extend(f"attempt {attempt}: {x}" for x in problems)

    print("\n=== validation summary ===")
    for case in cases:
        status = "ok" if case["name"] not in failures else "MISMATCH"
        print(f"{case['name']:<28} {status}")
        for problem in failures.get(case["name"], []):
            print(f"    - {problem}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
