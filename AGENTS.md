# Agentic Tourism MCP Recommender

## Source of truth

- Use `PLAN.md` as the implementation specification.
- Implement the project incrementally in the numbered phases recorded in `logs/`.
- Before starting a phase, read its log; after completing it, update that log with implementation details, decisions, validation, and any follow-up.
- Do not silently change an API contract or architecture decision from `PLAN.md`; record necessary deviations in the relevant phase log.
- Before any code implementation, explain the intended changes and wait for explicit user confirmation.
- Immediately before making code changes, state exactly: `I am coding`.
- Whenever an implementation log is updated, state exactly: `I wrote to logs`.
- Keep all work within the project folder unless the user explicitly approves an exception.

## Implementation sequence

1. Establish the project scaffold, dependencies, and database schema/seed setup.
2. Create the four MCP server modules and expose the tool contracts from `PLAN.md`.
3. Implement logistics behavior: city filtering, geographic travel calculations, and opening-hours checks.
4. Implement profiling behavior: text vibe extraction, visitor profiles, and compatibility scoring.
5. Implement the constraint and itinerary engine with feasible scheduling and route optimization.
6. Implement the orchestrator and prompt contract across all MCP tools.
7. Add constraint and benchmark evaluations, documentation, and run the complete validation suite.

## Step management

- Track each step's status in `logs/step-00-implementation-sequence.md`.
- Use these statuses: `Not started`, `In progress`, `Blocked`, and `Complete`.
- Before beginning a step, explain the intended work and wait for explicit user confirmation.
- A step is `Complete` only when its defined goal succeeds and all relevant tests pass.
- If a later step requires changing an earlier step, backtrack explicitly, update the affected implementation, and revalidate that step and every subsequent completed step.

## Engineering requirements

- Preserve the tool names, parameters, and return shapes specified in `PLAN.md` unless a logged decision documents the change.
- Keep server boundaries explicit; shared computation belongs in `core/`.
- Validate inputs at public tool boundaries and return explicit, useful errors.
- Enforce destination, opening-hours, travel-time, dwell-time, and itinerary-window constraints in code rather than relying on the orchestrator.
- Follow test-driven development as the default guideline: begin each implementation change with a focused test, then write the code needed to satisfy it. Deviate when practical constraints justify it, and record the reason.
- Maintain both module-level tests and integration tests as components are connected.
- Run the smallest relevant test set during development and the broader suite before completing a step.
- Inspect existing dependencies before adding new ones. Add a dependency only when it is genuinely needed, compatible with the project, and not duplicative or bloating.
- Follow general security practices, including input validation, safe handling of secrets, and least-privilege defaults.
- Keep generated databases, model caches, and other runtime artifacts out of source control unless explicitly required.
- Do not modify unrelated files or pre-existing user changes.

## Logging

- Store phase records as Markdown files under `logs/` using names such as `step-01-scaffold-and-database.md`.
- Logs track only code or project-structure changes; do not log Markdown-only documentation updates.
- Each record must state the scope implemented, files changed, important decisions, validation commands/results, and remaining risks or follow-up work.
- Record significant alternatives considered, dependency decisions, deviations from TDD, backtracking, and integration-test results.
- Keep logs factual and concise; do not use them as a substitute for source documentation.

## Completion reporting

- Completion responses must summarize changed files, validation results, remaining risks, and the current step statuses.
- Do not mark a step complete until implementation, validation, and its log entry are finished.
