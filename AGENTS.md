# AGENTS.md

Scope: this file applies to all work in this repository.

## Shared Coding Rules

For implementation, code review, tests, refactors, dependency decisions, and
debugging, follow `/Users/arthurlee/src/assistant/docs/CODING_AGENT_RULES.md`
when working on Arthur's machine. Explicit client instructions and nearer
workspace instructions override this file.

## Project Contract

- Canonical check command: `make ci`
- Durable state surfaces: `CHECKPOINT.md`, `logs.md`, and `executor_tasks.md`
  when task-level handoff is useful.
- For medium/risky work, name acceptance criteria, failure cases, evaluator
  inputs, verification commands, and evidence paths before broad execution.
- Keep client-sensitive evidence local unless the client-facing distribution
  explicitly allows it.

## Repo Notes

- Read `README.md`, package metadata, and nearby tests before changing behavior.
- Preserve existing package-manager, formatter, and test conventions.
- Do not commit secrets, credentials, private customer data, or local-only
  generated outputs.
