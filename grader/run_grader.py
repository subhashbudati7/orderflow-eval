#!/usr/bin/env python3
"""Grade one candidate tree.

    python run_grader.py                                  # the shipped (buggy) code
    python run_grader.py --patch ../patches/reference.patch
    python run_grader.py --source /path/to/agent/environment --label claude-run-3

Steps: copy the environment, apply the patch if any, run the repo's unit tests
(UNIT-01), bring the stack up with docker compose, run the integration
scenarios, write results/runs/<label>/report.json and summary.md.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from grader.config import ENVIRONMENT_DIR, ROOT  # noqa: E402
from grader.scoring import SCENARIOS, Outcome, summarize  # noqa: E402

RUNS_DIR = ROOT / "results" / "runs"


def log(msg: str) -> None:
    print(f"[grader] {msg}", flush=True)


def prepare_tree(source: Path, patch: Path | None, workdir: Path) -> Path:
    tree = workdir / "environment"
    shutil.copytree(source, tree, ignore=shutil.ignore_patterns("target", ".git", "__pycache__"))
    if patch:
        log(f"applying {patch.name}")
        service = tree / "order-service"
        # git apply works outside a repo with --unsafe-paths... simpler to just init one.
        subprocess.run(["git", "init", "-q"], cwd=service, check=True)
        subprocess.run(["git", "add", "-A"], cwd=service, check=True)
        subprocess.run(["git", "-c", "user.email=g@x", "-c", "user.name=g", "commit", "-q", "-m", "base"],
                       cwd=service, check=True)
        res = subprocess.run(["git", "apply", "--whitespace=nowarn", str(patch)], cwd=service,
                             text=True, capture_output=True)
        if res.returncode != 0:
            raise SystemExit(f"patch did not apply:\n{res.stderr}")
    return tree


def run_unit_tests(tree: Path, out_dir: Path) -> Outcome:
    service = tree / "order-service"
    started = time.monotonic()
    if shutil.which("mvn"):
        cmd = ["mvn", "-q", "-B", "test"]
        cwd = service
    else:
        log("mvn not found locally, running unit tests in a maven container")
        cmd = ["docker", "run", "--rm", "-v", f"{service}:/src", "-w", "/src",
               "-v", f"{Path.home() / '.m2'}:/root/.m2",
               "maven:3.9-eclipse-temurin-21", "mvn", "-q", "-B", "test"]
        cwd = None
    res = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    (out_dir / "mvn-test.log").write_text(res.stdout + "\n" + res.stderr)
    passed = res.returncode == 0
    detail = "" if passed else tail(res.stdout + res.stderr)
    return Outcome("UNIT-01", passed, time.monotonic() - started, detail)


def tail(text: str, n: int = 40) -> str:
    lines = [l for l in text.splitlines() if l.strip()]
    return "\n".join(lines[-n:])


def run_scenarios(tree: Path, out_dir: Path, pytest_args: list[str]) -> list[Outcome]:
    results_json = out_dir / "scenarios.json"
    env = dict(os.environ, GRADER_COMPOSE_DIR=str(tree), PYTHONDONTWRITEBYTECODE="1")
    cmd = [sys.executable, "-m", "pytest", "grader/scenarios", "-q", "-rA", "-p", "no:cacheprovider",
           f"--results-json={results_json}", *pytest_args]
    with open(out_dir / "pytest.log", "w") as fh:
        subprocess.run(cmd, cwd=HERE, env=env, stdout=fh, stderr=subprocess.STDOUT, text=True)
    if not results_json.exists():
        raise SystemExit(f"pytest produced no results; see {out_dir / 'pytest.log'}")
    raw = json.loads(results_json.read_text())
    return [Outcome(**r) for r in raw]


def write_report(out_dir: Path, label: str, source: str, patch: str | None,
                 outcomes: list[Outcome], meta: dict) -> dict:
    summary = summarize(outcomes)
    report = {
        "label": label,
        "graded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "patch": patch,
        "summary": summary.to_dict(),
        "scenarios": [o.__dict__ for o in sorted(outcomes, key=lambda o: o.scenario)],
        "meta": meta,
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2))

    lines = [f"# {label}", "",
             f"Result: **{'PASS' if summary.passed else 'FAIL'}**  "
             f"(score {summary.score:.0f}/{summary.max_score})", ""]
    if patch:
        lines.append(f"Patch: `{patch}`\n")
    lines += ["| scenario | kind | result | note |", "|---|---|---|---|"]
    for o in sorted(outcomes, key=lambda o: o.scenario):
        s = SCENARIOS[o.scenario]
        note = o.detail.splitlines()[-1][:120] if o.detail else ""
        lines.append(f"| {o.scenario} | {s.kind} | {'pass' if o.passed else 'FAIL'} | {note} |")
    lines += ["",
              f"Bugs fixed: {', '.join(summary.bugs_fixed) or 'none'}",
              f"Bugs remaining: {', '.join(summary.bugs_remaining) or 'none'}",
              f"Regressions: {', '.join(summary.regressions) or 'none'}", ""]
    (out_dir / "summary.md").write_text("\n".join(lines))
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", type=Path, default=ENVIRONMENT_DIR,
                   help="environment directory to grade (default: the shipped one)")
    p.add_argument("--patch", type=Path, default=None, help="git patch applied inside order-service/")
    p.add_argument("--label", default=None, help="name for the results folder")
    p.add_argument("--skip-unit-tests", action="store_true")
    p.add_argument("--keep-tree", action="store_true", help="leave the prepared copy on disk")
    p.add_argument("--exit-zero", action="store_true", help="exit 0 even when the candidate fails")
    p.add_argument("pytest_args", nargs="*", help="extra args after --, passed to pytest")
    args = p.parse_args(argv)

    label = args.label or (args.patch.stem if args.patch else "baseline")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = RUNS_DIR / f"{stamp}-{label}"
    out_dir.mkdir(parents=True, exist_ok=False)
    log(f"results -> {out_dir}")

    workdir = Path(tempfile.mkdtemp(prefix="orderflow-grade-"))
    try:
        tree = prepare_tree(args.source.resolve(), args.patch.resolve() if args.patch else None, workdir)
        outcomes: list[Outcome] = []
        if args.skip_unit_tests:
            log("skipping UNIT-01 (treated as failed in the summary)")
        else:
            log("running repository unit tests")
            unit = run_unit_tests(tree, out_dir)
            log(f"UNIT-01 {'pass' if unit.passed else 'FAIL'}")
            outcomes.append(unit)

        log("running integration scenarios (this starts docker compose)")
        outcomes += run_scenarios(tree, out_dir, args.pytest_args)

        meta = {
            "grader_version": "0.3.0",
            "python": sys.version.split()[0],
            "docker": subprocess.run(["docker", "--version"], text=True, capture_output=True).stdout.strip(),
            "env": {k: v for k, v in os.environ.items() if k.startswith("GRADER_")},
        }
        report = write_report(out_dir, label, str(args.source), str(args.patch) if args.patch else None,
                              outcomes, meta)
    finally:
        if args.keep_tree:
            log(f"prepared tree kept at {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)

    s = report["summary"]
    log(f"{'PASS' if s['passed'] else 'FAIL'}  score {s['score']}/{s['max_score']}  "
        f"bugs remaining {s['bugs_remaining']}  regressions {s['regressions']}")
    print((out_dir / "summary.md").read_text())
    return 0 if (s["passed"] or args.exit_zero) else 1


if __name__ == "__main__":
    sys.exit(main())
