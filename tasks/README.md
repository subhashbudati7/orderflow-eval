# tasks

One JSON file per task given to a coding agent. The file is the single place
that says what the agent sees, what it may touch, how long it gets and how it
is graded. Agent harnesses read `prompt`, `working_directory` and `budget`;
humans read the rest.

`known_traps` is for the people running the eval, never for the agent. It
lists the wrong turns the incomplete patches in `patches/incomplete/`
represent, so when an attempt fails you can tell quickly whether it hit a
known trap or found a new way to be wrong (which goes in
`results/findings.md`).

Adding a task means adding a bug report, a grader scenario set, a reference
patch and an expected-outcomes file. Don't add the JSON first.
