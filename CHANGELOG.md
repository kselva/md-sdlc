# Changelog

## 0.4.0 — 2026-10-26

Short layout, one-screen status, experiments, and upkeep commands. Driven by
the first adopter dropping the tool (long paths, unused `tasks.md`, hand
edits) - see `PROPOSAL-0.4.0-short-layout-status-and-experiments.md`.
Classic projects keep working unchanged (the 35 existing tests pass as is).

- New opt-in `id_style: short` with `work_dir`, `decision_waits`,
  `stale_days` in `.sdlc/config.yml`; `init --id-style --work-dir`.
  Short ids (`PAY1`, `PAY1-A`, `PAY1-A.3`, `PAY1-E2`, `IDEA-x`) and names of
  id + up to 3 words. CONVENTIONS §14.
- New commands: `status [ID] [--json]`, `set`, `item add|set`, `log`, `adopt`.
- New status `parked` (not terminal), type `experiment`, scenarios `poc` and
  `quality`, header fields `title`, `next`, `waits_on`, `deployed`,
  `question`, `result`, `verdict`, `adopted`.
- `core/overview.py`: status as plain data; terminal text, `backlog.md`
  (short layout) and `--json` all render it - the seam for a later UI.
- `validate`: duplicate ids and unknown verdicts are errors (both layouts);
  short-layout rules (loose files, id/name agreement, story under its epic;
  warnings for long names and open items without `next`).
- `new`: short ids/paths, `--code`, `new experiment --question`; epic/story
  get `tasks.md` + `log.md`; `new task` points to `item add` in short layout.
- `promote --to-epic` keeps every Proposal header field; `--code` in short layout.
- Fixes: the parsed tree is cached (status on 2,000 files well under 2 s
  once files are on disk); header writes keep key order; row tables are read
  by header name and allow `\|` in a cell; `archive` refreshes the cache.

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
- New `stats` command — status statistics without opening every file:
  `stats` (project-wide type × status matrix, plus a `stability` tally and
  an open-findings-by-severity line), `stats --epic <id>` (one Epic's
  Stories and Tasks broken down, plus a per-Story table), `stats --by
  owner|stability|scenario` (counts grouped by that field), `stats --json`.
- `query --unresolved-reviews` no longer requires `--story` — omit it for a
  project-wide sweep of every Story's open / changes-requested findings in
  one table.
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
