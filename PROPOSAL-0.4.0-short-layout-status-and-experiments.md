# Proposal - md-sdlc 0.4.0: short layout, one-screen status, experiments

Status: approved 2026-10-26, built in 0.4.0
Date: 2026-10-26
Target version: 0.4.0

## 1. Why

A second project wants to adopt md-sdlc. The first adopter dropped it after
five days. Its archived tree shows why:

| Seen | Detail |
|---|---|
| Names too long | folder name = full title; paths up to 158 characters |
| Same words repeated | the project name inside every Epic folder name |
| `tasks.md` never used | 74 Stories, 0 `tasks.md` files - editing a table by hand was skipped |
| Own files beside the rules | `implementation-brief.md`, `session-notes.md` - unknown to the tool |
| Work moved outside | plain `PLAN-*.md` files were quicker than Epic + Story |
| Rollup too thin | `backlog.md` = Epic, status, stories done/total, owner. No "what next", no "waiting on whom" |

The second project also needs to track POCs, quality experiments (replays,
threshold tests) and ideas, and wants the overall status from the tool.

## 2. Assessment of 0.3.0 (code read 26-10, 35 tests pass)

### Solid
- One class touches the filesystem (`AiDocsRepo`); every command is a plugin
  behind `BaseCommand`. Adding a command = one folder.
- `validate` gives schema, vocabulary and link checks; files without a
  header are ignored, so a project can adopt it gradually.
- Rollups are generated, never hand-edited.
- About 2,700 lines, small enough to change safely.

### Weak (fixed in 0.4.0 unless marked)
| # | Weakness | Effect |
|---|---|---|
| W1 | `find()`, `children_of()`, `task_rows()` each re-walk the whole tree | slow as the tree grows (n x n); fine at 300 files, not at 3,000 |
| W2 | header writes re-sort keys (yaml default `sort_keys=True`) | every write reorders a hand-written header |
| W3 | `promote --to-epic` rewrites the Proposal header with a fixed key list | any extra field (title, links) is lost |
| W4 | row tables read by column position | a table with a column added or reordered silently misreads |
| W5 | no duplicate-id check | two files with one id: `find()` returns the first, silently |
| W6 | plugins `print()` directly; only `stats` has `--json` | a UI would have to scrape text |
| W7 | frozen-exe plugin list kept in two places | known trap, documented; not changed |
| W8 | no way to change a header except by hand | upkeep cost - the main reason it was dropped |

### Extendability and a UI later
The plugin seam is good for new commands. The missing piece for a UI is a
layer that returns data instead of printing it. 0.4.0 adds `core/overview.py`:
one function builds the status as plain data; the terminal view, the
generated `backlog.md` and `--json` all render that same data. A later UI
(a local read-only web page, or a static `backlog.html`) reads the same data
and calls the same write functions the commands use - no second copy of the
rules. A UI is not built in 0.4.0.

## 3. Design

### 3.1 Short layout (opt-in per project)
`.sdlc/config.yml`:
```yaml
id_style: short        # default "classic" - existing projects unchanged
work_dir: plan         # where new items are created (default: project root)
decision_waits: owner  # waits_on value that means "decision waiting for the owner"
```

| Item | Id | Path |
|---|---|---|
| Epic (track) | code you pick, e.g. `PAY1` | `plan/PAY1-checkout/epic.md` |
| Story (step) | `<epic>-<code>`, e.g. `PAY1-A` | `plan/PAY1-checkout/PAY1-A-card-form/story.md` |
| Open item (row) | `<story or epic>.<n>`, e.g. `PAY1-A.3` | row in `tasks.md` |
| Experiment | `<parent>-E<n>`, e.g. `PAY1-E2` | `plan/PAY1-checkout/PAY1-E2-retry-rate.md` |
| Proposal (idea) | `IDEA-<slug>` | `plan/ideas/IDEA-saved-cards.md` |
| Ad hoc | `ADHOC-<slug>` | `plan/ADHOC-<slug>.md` |

- Folder/file name = id + up to 3 words. `new` cuts longer titles. The full
  title goes in a `title:` header field.
- Search by id finds everything: the id is at the front of every name.

### 3.2 Fixed files in an item folder
| File | Holds |
|---|---|
| `epic.md` / `story.md` | the plan for the item, with the header |
| `tasks.md` | open items as rows: `id \| status \| waits \| verdict \| updated \| summary` |
| `log.md` | dated notes, newest first |
| any other file | allowed; shown as "attached" to that item |

### 3.3 Header fields added
`title`, `next` (one line), `waits_on` (free word; `decision_waits` value
means a decision for the owner), `deployed` (what is live and since when -
the "On site" section), `adopted`, and for experiments `question`, `result`,
`verdict` (`yes` / `no` / `partly` / `open`). A quick experiment can
also be a row with a verdict (`item add --experiment`).

### 3.4 Words added
- Status `parked` - not terminal, can come back; has its own section.
- Type `experiment` (work-item) - one question, one result.
- Scenarios `poc`, `quality`.

### 3.5 Commands
| Command | Does |
|---|---|
| `status [ID] [--json]` | one screen: done/now/later counts; on site (`deployed`); blocked; waiting on others; tracks (state, steps done/total, open items, next, waits on, updated); waiting for check (`in-review` + rows waiting); decisions for the owner; experiments with question/verdict; last 10 changes; not touched 14 days; ideas; parked. With an id: that item and all its open rows |
| `backlog` | in short layout writes the same as `status` to `backlog.md` (classic unchanged) |
| `set ID --status --next --waits-on --result --verdict` | change header fields, sets `updated` |
| `item add PARENT "text" [--waits X]` / `item set ROW-ID STATUS [--waits X]` | add / change rows, sets the date |
| `log ID "text"` | dated line on top of `log.md`, sets `updated` |
| `adopt FILE --type --id [--parent --status --title]` | adds a header to an existing file in place, no move |
| `new` | short-layout ids and paths; `--code`; `new experiment --question` |

### 3.6 Rules `validate` enforces in short layout (simple and fixed)
ERROR:
1. Every `.md` under `work_dir` is either a tracked item, `tasks.md`,
   `log.md`, or inside a tracked item's folder. A loose file is an error:
   "adopt it or move it".
2. Ids unique (W5).
3. A Story id starts with its Epic id; an item folder/file name starts with its id.
4. Known type, status, scenario, verdict; rows use the status words.
5. Every link (parent, related, ...) resolves.

WARNING:
6. Folder or file name longer than 40 characters.
7. An open Epic/Story (in-progress, in-review, blocked) with no `next:`.

## 4. Scenarios to check (each becomes a test on a temporary tree)

| # | Scenario | Expected |
|---|---|---|
| S1 | new track + 2 steps + 3 open items | `status` lists track, 0/2 steps done, 3 open items |
| S2 | step built, sent for a field check (`set --status in-review`) | listed under "waiting for check" |
| S3 | open item `--waits site` | listed under "waiting on others" with the row id |
| S4 | `set --waits-on owner` | listed under "decisions for the owner" |
| S5 | `set --status parked` | moves from tracks to "parked"; `validate` OK |
| S6 | item not updated for 15 days | listed under "not touched 14 days" |
| S7 | idea -> promote to track | Epic created with short id, idea `done` with link, idea's extra fields kept (W3) |
| S8 | POC: track `scenario: poc` with 2 experiments | experiments listed with question + verdict |
| S9 | experiment result recorded with `set --result --verdict yes` | shown in status; header order unchanged (W2) |
| S10 | old loose plan file `adopt`-ed in place | tracked; not moved, body unchanged |
| S11 | loose file left in `plan/` | `validate` ERROR naming the file |
| S12 | duplicate id / bad parent / unknown verdict | `validate` ERROR each |
| S13 | name 60 characters / open step without `next` | `validate` WARNING each |
| S14 | `log` twice | newest line on top, `updated` = today |
| S15 | track `done` -> `archive` | moves to `hist/`; gone from status; links to it still resolve |
| S16 | `tasks.md` hand-edited with columns reordered, text with `\|` | rows read by header name; escaped pipe kept |
| S17 | `status --json` | same numbers as the text view |
| S18 | classic project (existing fixtures) | all 35 existing tests still pass |
| S19 | 2,000 generated files | `status` under 2 seconds (W1 cache) |

## 5. Not in 0.4.0
UI, Jira sync, cross-project view, automatic parking (status only lists
stale items; a person decides).

## 6. Delivery
1. Core: cache (W1), key order (W2), header-mapped rows (W4), duplicate ids
   (W5), `core/overview.py` (W6), header update helper (W8).
2. Vocab + config: `parked`, `experiment`, scenarios, `id_style`, `work_dir`,
   `decision_waits`.
3. Commands: `status`, `set`, `item`, `log`, `adopt`; `new`, `backlog`,
   `promote` (W3), `validate` short-layout rules.
4. Frozen list + spec for the 5 new plugins; rebuild exe.
5. Tests S1-S19; CONVENTIONS "short layout" section (one page, the rules
   above); README; CHANGELOG; version 0.4.0.
