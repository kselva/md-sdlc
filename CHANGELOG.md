# Changelog

## 0.3.0 — 2026-08-30

Stability gate, agent handover pack, and collision guards. Driven by real
adoption pain on a project built largely by AI coding agents (see
`PROPOSAL-0.3.0-stability-gate-and-agent-handover.md`). No change to the
core type/status model, rollup generation, or marker discovery — net
effect is a *lighter* process.

- New `stability` field on `epic` / `story` — `exploring` / `settled` /
  `locked`. Gates how much test ceremony is allowed while the customer is
  still changing behaviour.
- `validate` test gate (all directory-listing only — never reads or runs a
  test):
  - ERROR: a `stability: exploring` Story with an assertion/spec test file
    under its `touches:` paths (a single `smoke_test_glob` match is exempt).
  - WARNING: a `stability: exploring` Story with a promoted `TASK-xx.md`
    file, or with `status: done`.
- `validate` findings are now split into ERRORS (exit 1) and WARNINGS
  (printed, exit 0).
- New `touches:` field on `story` — advisory list of repo-relative path
  globs. `validate` emits a WARNING when two active Stories' `touches:`
  overlap. Never checked against the filesystem.
- New `handover <story-id>` command — prints a one-Story context pack
  (branch, `AI-RULES.md`, story body, open task rows, `touches:`, linked
  artifacts, open review findings) for pasting to an AI agent. `--full`
  inlines linked artifact bodies; `--strict` refuses if `validate` fails.
- New `query --active` — one line per in-progress / in-review Story with
  branch and `touches:` globs, for eyeballing collisions before handing
  out new work.
- `init` now ships an `AI-RULES.md` template and writes it to the project
  root (~30-line behavioural contract, one per project).
- `.sdlc/config.yml` gains optional keys: `code_root`, `test_file_globs`,
  `smoke_test_glob`.
- `CONVENTIONS.md` — `stability` / `touches` added to §8; new §10 (stability
  and the test gate) and §11 (sample-data / golden-file development);
  "what the tool will never do" renumbered to §12.

## 0.2.0 — 2026-08-19

Added multi-agent/multi-person review handoff support.

- New `review` command — `report` (reviewer adds a finding) and `resolve`
  (author marks it fixed/wontfix/changes-requested).
- New `review.md` file convention — sibling to `tasks.md`, same row-table
  pattern, own status vocabulary (`open`, `changes-requested`, `fixed`,
  `wontfix`). Kept separate from `tasks.md` because a finding is feedback on
  work already done, not planned work.
- New `in-review` work-item status, between `in-progress` and `done`.
- `validate` now checks `review.md` rows (duplicate ids, valid status) the
  same way it checks `tasks.md` rows.
- `CONVENTIONS.md` §5 documents the full review workflow; renumbered §5-§8
  to §6-§9 accordingly.

## 0.1.0 — 2026-08-18

Initial release. Epic/Story/Task/Proposal/Ad hoc tracking via markdown +
frontmatter, git-style `.sdlc/` project discovery, plugin-based CLI
(`init`, `validate`, `backlog`, `query`, `new`, `promote`, `archive`,
`conventions`), compiled to a standalone Windows exe via PyInstaller.
