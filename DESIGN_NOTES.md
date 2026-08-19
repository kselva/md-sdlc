# Design Notes

Why the tool looks the way it does, and what's still open. `CONVENTIONS.md`
is the enforceable rule set; `CHANGELOG.md` is what shipped when; this file
is the reasoning that produced both, kept so a later session (human or
agent) can continue without re-deriving decisions already made.

## 1. The core problem this solves

JIRA-style tracking (Epic/Story/Task hierarchy, status, backlog view) without
running JIRA — using folders and markdown as the "database," a small CLI as
the "database engine." The explicit goal was **not** to build a JIRA clone;
it was to get the parts of JIRA that matter (hierarchy, status visibility,
a rollup you don't have to hand-maintain) using files anyone can read and
edit with a text editor.

## 2. The database analogy (why this isn't just "some markdown files")

Early on, the design was pressure-tested against what a real database gives
for free that a flat-file scheme doesn't:

| Gap | DB solves it via | This tool's answer |
|---|---|---|
| No enforced schema | Rejects malformed rows | `validate` — required frontmatter fields, allowed vocab |
| No transactional consistency | Views auto-refresh | `backlog.md` is **generated**, never hand-edited — nothing to go stale |
| No real query engine | `WHERE ... AND ...` | `query`'s filter flags — a real but *bounded* ceiling, no joins/aggregations |
| No referential integrity | Rejects a dangling FK | `validate` checks every `parent`/`related`/etc. resolves |

The conclusion: these gaps are closeable with *process*, not just hope — but
closing them means the discipline has to be enforced by a tool, not by
memory. That's why `validate` exists and why generation (not hand-editing)
of rollups was non-negotiable from the start.

## 3. Why Epic / Story / Task / Proposal / Ad hoc (and not just "Task")

Walked through real JIRA-equivalent scenarios (new feature, bug, hotfix,
R&D, POC, brainstorm, weekly report, resuming old work — see git history of
the conversation that produced this tool, or re-derive from `CONVENTIONS.md`
§1/§6) before settling on five structural types. The two non-obvious ones:

- **Proposal** exists because "committed work" and "an idea being
  evaluated" are different things — a Proposal doesn't get Epic-level
  folder scaffolding until it's accepted. Acceptance is a **spawning
  event** (creates a new Epic file, doesn't just flip a status), captured
  via `originated_from:`.
- **Ad hoc** exists because hotfixes/rollbacks/R&D genuinely don't have a
  parent Story at the time they're created — forcing one would be fiction.
  An Ad hoc item can later be folded into planned work (`promote`), but
  isn't required to be.

## 4. Why two status vocabularies, not one

A work-item (Epic/Story/Task/Adhoc/Proposal) has a *lifecycle* — it starts
somewhere, moves through states, ends somewhere. An artifact (a design doc,
a benchmark result, a report) doesn't — it's either accurate or it's been
replaced. Using one shared vocabulary for both was tried conceptually and
rejected: "done" means "finished" for a task and "no longer needed" for
nothing in particular for a doc — the words don't actually mean the same
thing, so sharing them would be misleading, not simplifying.

`blocked` vs `abandoned` was modeled on how JIRA actually separates *status*
(is this still active) from *resolution* (why did it end) — confirmed via
research before adopting: `blocked` is temporary and returns to
`in-progress`; `abandoned` is terminal and reachable from any state,
covering "rejected proposal" too so it didn't need its own word.

`in-review` (added later, see §7) was the one gap found once a real
multi-agent review workflow was worked through — the vocabulary wasn't
wrong, it was incomplete for a scenario not yet considered when it was
first written.

## 5. Why row-tables (tasks.md, review.md) instead of one-file-per-item always

Pushback during design: at real scale (100 Stories, 1000 Tasks), one file
per Task means mostly-empty files dominated by frontmatter boilerplate.
The resolution was **hybrid by size** — small/simple records live as table
rows; a record graduates to its own file only once it needs more than a row
can hold (a design doc, a long discussion, multiple dated status changes).
This is the same "flat until it doesn't fit" rule applied at the file level
(§2 of `CONVENTIONS.md`, "1-3 files flat, 4+ needs a subfolder") pushed down
one level, to rows within a file.

`review.md` (added in 0.2.0) reuses this exact pattern rather than
inventing a new one — same row-table parsing code (`AiDocsRepo._read_row_table`
is now shared between `task_rows()` and `review_rows()`), different column
set and status vocabulary.

## 6. Why git-style `.sdlc/` marker discovery, not a central config registry

The first version used one `config.yml` inside the tool listing every
tracked project's path (`profiles: { sto_code: { path: ... } }`). Replaced
because a central registry is exactly the kind of thing this whole design
was trying to avoid elsewhere — a hand-maintained pointer that silently
drifts (a project moves, the registry doesn't get updated, and nothing
tells you it's wrong). Marker discovery (`ai-docs/.sdlc/config.yml`, found
by walking up from cwd like `git` finds `.git/`) removes the registry
instead of trying to keep it in sync. This was a full redesign mid-project,
not a tweak — worth knowing if `core/profile.py`'s current shape looks like
it was designed this way from day one; it wasn't.

## 7. Why a compiled exe exists

Originally just `python sdlc_tool.py ...`. Two real problems with that:
"which Python" is ambiguous once multiple projects each have their own venv
on `PATH` (confirmed during development: `python` was resolving to a
*different* project's venv, not a real global interpreter), and requiring
`pip install` before first use is friction for a tool meant to be dropped
into any project. PyInstaller removes both. Two non-obvious build issues
this produced, worth knowing before adding a 9th plugin:

- **Plugin discovery breaks when frozen.** Dev mode walks `plugins/` on
  disk; PyInstaller's `--onefile` mode extracts to a temp dir at runtime and
  only bundles files it can trace via static imports — a dynamically
  `importlib`-loaded plugin folder is invisible to it. Fixed via a
  `sys.frozen` check in `plugins/__init__.py` that falls back to a fixed
  module list when frozen.
- **That fixed list has to be updated in TWO places** — `plugins/__init__.py`'s
  `_FROZEN_PLUGIN_MODULES` AND `md_sdlc.spec`'s `hiddenimports`. Missing
  either one means the command silently works under `python sdlc_tool.py`
  but is missing entirely from the compiled exe. This bit twice during
  development (once adding `conventions`, once adding `review`) — both
  files now have an explicit comment pointing at the other, but this is
  still a real trap for whoever adds plugin #9.
- Data files (Jinja templates, `CONVENTIONS.md`) need explicit `datas=[...]`
  entries in `md_sdlc.spec` for the same reason — they're not Python
  imports, so static analysis never sees them.

## 8. What's deliberately not built (and why)

Not oversights — evaluated and explicitly deferred:

- **Cross-project aggregation.** Each project is targeted independently via
  `.sdlc/` marker discovery; there's no "show me everything blocked across
  all my projects" query. Would need a way to enumerate known projects
  without reintroducing the central-registry problem §6 just removed —
  not solved, not attempted yet.
- **Jira/ADO sync.** A working `jira_client.py` already exists in a
  sibling toolkit (`or-tools/azure-devops-tools/`) and could back a future
  `jira_sync` plugin. Not built — this tool was explicitly scoped as a
  *local-first* system, not a staging layer for a real tracker, though the
  plugin architecture leaves the seam open if that changes.
- **Migration of pre-existing docs.** The convention applies going forward
  only. A migration tool (walk old free-form docs, infer type/status,
  generate frontmatter) is a distinct, harder problem — not attempted.
- **Enforced writing quality.** `validate` checks that fields exist and
  resolve; it cannot check that a Task's content is actually resumable by
  someone else later. No tooling fix for this — it's a discipline
  requirement, same as it would be in real JIRA.
- **Arbitrary querying.** `query`'s filter flags (type/status/owner/
  scenario/staleness) are the ceiling — no joins, no aggregation beyond
  simple counts. Accepted as the honest limit of a flat-file system without
  a real query engine behind it.

## 9. Real bugs found during development (worth knowing before touching that code)

- `new`'s `_NO_PARENT_TYPES` initially didn't include `epic`, so creating a
  top-level Epic wrongly demanded `--parent`.
- `promote --to-epic` didn't create the target directory before writing —
  `mkdir(parents=True, exist_ok=True)` was missing (present in `new`, absent
  in `promote` — copy-paste gap between two similar write paths).
- `core/frontmatter.py`'s `write()` opened the file in binary mode but
  `frontmatter.dumps()` returns `str` — crashed on every `promote`-driven
  write until fixed to text mode.
- A promoted `tasks.md` row initially left a fake status value (`"-> promoted"`)
  in place instead of removing the row — `validate` correctly rejected it
  as an invalid status, which is what caught the bug.
- Windows console codepage (`cp1252`) can't encode the arrow/box-drawing
  characters in `CONVENTIONS.md` — `md_sdlc conventions` crashed on
  `print()` until switched to writing UTF-8 bytes directly to
  `sys.stdout.buffer`.

None of these are currently live bugs — listed so the *shape* of past
mistakes (copy-paste gaps between similar code paths, frozen-vs-dev-mode
divergence, encoding assumptions) is visible before making similar changes.

## 10. Where things stand (as of 0.2.0, 2026-08-19)

- Real adoption: one project's `ai-docs/` tree has 30 real Epics tracked,
  `validate` passes clean.
- Public repo: `github.com/kselva/md-sdlc`, description/topics set.
- A global Claude Code instructions file and at least one project-specific
  Amazon Q rules file have been updated to point at `md_sdlc conventions`
  as the source of truth instead of hardcoding folder rules — meaning the
  convention can evolve in one place without hunting down every rule file
  that quoted it.
- Nothing outside `md-sdlc` itself has been taught about `review.md`/
  `in-review` yet beyond what's in this repo's own docs — if other
  projects' rule files reference specific commands, they may need a note
  that `review` exists now.
