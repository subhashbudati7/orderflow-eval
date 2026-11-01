# Attempt: <date>-<model>-<n>

## Setup (fill in before grading)

| field | value |
|---|---|
| task | orderflow-ord-2291 v1 |
| model | e.g. claude-sonnet-4.5, gpt-5-codex |
| model version / date string | exact identifier from the API or UI |
| harness | e.g. Claude Code 2.x, Codex CLI, custom loop |
| tools available | shell, file edit, docker? network? |
| budget given | N turns / N minutes |
| budget used | N turns / N minutes |
| temperature / sampling | if known |
| run folder | results/runs/<stamp>-<label> |

## Grader result

Paste `summary.md` from the run folder.

Pass: yes / no
Bugs fixed:
Bugs remaining:
Regressions:

## What the agent did

Chronological, short. What it read first, whether it reproduced anything,
what it changed, in what order, whether it ran the unit tests, whether it
brought the stack up.

## Why it failed (if it did)

One paragraph per failing scenario. Link to the exact diff hunk and quote the
transcript where the agent justified the choice.

Known trap hit (from tasks/*.json `known_traps`): yes / no / which

## Grader notes

Anything the grader did that was wrong, unclear or flaky during this attempt.
Copy into results/findings.md too.

## Transcript excerpts

```
<verbatim lines that explain the interesting decisions>
```
