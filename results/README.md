# results

Everything an agent run produces lands here. Nothing in this folder is
hand-edited except `attempts/*.md` and `findings.md`.

```
results/
  runs/          one folder per grader invocation: report.json, summary.md,
                 pytest.log, mvn-test.log, scenarios.json  (git-ignored)
  attempts/      one markdown file per agent attempt, written by a human,
                 from attempts/TEMPLATE.md
  findings.md    cross-attempt notes: failure modes, grader fixes, open questions
  last-run/      order-service.log from the most recent compose stack (git-ignored)
```

## Recording an attempt

1. Copy `attempts/TEMPLATE.md` to `attempts/<date>-<model>-<n>.md`.
2. Fill in model, version string, budget, tools, before looking at the result.
   Writing those down afterwards is how numbers drift.
3. Run the grader on the agent's tree and paste the summary table.
4. Pull the relevant lines from the agent transcript into the "what it did"
   section. Quote, don't paraphrase, when the agent explains a wrong decision.
5. If the grader did something surprising (flaky scenario, unclear failure
   message, passed something it shouldn't have) that goes in `findings.md`
   under "grader", with the run folder name.

## What to compare across attempts

- Which bug scenarios each attempt fixed. IDEM-01 tends to be found first.
- Whether the attempt fell into a `known_traps` entry from the task JSON.
- Regressions introduced (contract scenarios that went red).
- Turns and wall clock used against the budget.
- Whether the agent ran the stack, or only read code and guessed.
