# Changelog

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
