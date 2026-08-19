# md-sdlc Conventions

The normative reference for naming, folder structure, and frontmatter schema.
This is what `validate` enforces and what `new`/`promote` generate. If a rule
here and the tool's behavior ever disagree, that's a bug in the tool.

(This file is the extracted, project-independent rule set — the enforceable
contract. Design rationale and history live separately, in whichever
project's own planning docs first worked through the model.)

## 1. Types and ID prefixes

The ID prefix is the type marker. No wrapper folder words needed.

| Type | ID prefix | Has children? |
|---|---|---|
| `proposal` | `PROPOSAL-<slug>` | No — spawns an Epic on acceptance |
| `epic` | `EPIC-<code>-<slug>` | Stories |
| `story` | `STORY-<nn>-<slug>` | Tasks |
| `task` | `TASK-<nn>-<slug>` | No |
| `adhoc` | `ADHOC-<slug>` | No — root-level, no committed parent |

Artifact types (no lifecycle, see §3): `analysis`, `design-lld`, `design-hld`,
`design-tech-notes`, `report`, `reference`, `guide`, `query`, `schema`.

## 2. Folder shape

Nesting communicates parent/child — a file's location expresses "this Task
belongs to this Story," no field required.

```
<project>/
  .sdlc/config.yml            # marker - created by `init`, never hand-edited
  backlog.md                  # generated - Epic-level view only
  hist/                       # archived terminal-status items
  PROPOSAL-<slug>.md          # flat, root level
  ADHOC-<slug>.md             # flat, root level
  EPIC-01-checkout-redesign/
    epic.md
    backlog.md                 # generated - Story+Task level, this Epic only
    STORY-01-payment-backend/
      story.md
      lld.md                    # flat if <=3 design docs, else design/ subfolder
      tasks.md                   # small tasks as rows (see §4)
      review.md                   # reviewer findings as rows (see §5)
      TASK-07-promoted-task.md   # a row promoted to its own file
    STORY-02-ui-integration/
      story.md
      TASK-01-format-fallback-badge.md
```

**Flat-vs-folder threshold** (files within one folder, not folder count):

| Count of an item type | Layout |
|---|---|
| 1-3 files | flat |
| 4+ files | subfolder named after what it holds (`design/`, `tasks/`) |

## 3. `kind`: work-item vs artifact

Every file declares which bucket it's in — this decides whether it has a
status lifecycle and whether it appears in `backlog.md` rollups.

| `kind` | Has a status lifecycle? | In rollups? | Types |
|---|---|---|---|
| `work-item` | Yes | Yes | proposal, epic, story, task, adhoc |
| `artifact` | No (filed and linked, no open/pending state) | No | analysis, design-*, report, reference, guide, query, schema |

`type -> kind` is a fixed lookup (`core/vocab.py`), not independently settable
— a file's `kind` can never disagree with its `type`.

## 4. Task storage — hybrid by size

Tasks **start** as rows in one `tasks.md` per Story (columns: `id | status |
scenario | owner | updated | summary`). A row is **promoted** to its own
`TASK-xx.md` file once it needs a design doc, a long discussion, or multiple
dated status notes (`md_sdlc promote <id> --to-file --story <story-id>`).

## 5. Review findings — multi-agent handoff

When one agent (or person) designs/codes a Story and a second reviews it,
findings go in `review.md`, a sibling to `tasks.md` using the same row-table
convention — kept separate from `tasks.md` because a finding is feedback on
work already done, not work that was planned.

```
| id | severity | status | summary | reported_by | updated |
|----|----------|--------|---------|--------------|---------|
| RVW-01 | critical | open | Race condition in retry logic | agent-2 | 2026-08-19 |
```

- **Reviewer** adds a finding: `md_sdlc review report --story <id> --summary "..." --severity <critical|high|medium|low> --reported-by <name>`
- **Author** resolves it after fixing: `md_sdlc review resolve RVW-01 --story <id> --status <fixed|wontfix|changes-requested>`
- Row status vocabulary is its own, separate from work-item status (§6):
  `open → changes-requested → fixed` / `wontfix`. There is no "not-started" —
  a finding exists because it was already found, not because it's queued.
- The Story's own `status:` (§6) can be `in-review` while its `review.md` has
  open rows — reviewing is a phase the Story sits in, findings are the
  granular record of what's blocking it from `done`.
- A finding is promotable the same way a task row is, if one needs a long
  fix discussion rather than a one-line resolution (not yet automated by
  `promote` — create the file by hand following the Task file shape in §1
  if a finding grows beyond a row).

## 6. Status vocabulary

Two vocabularies, kept separate because the same word means different things
for a unit of work versus a reference document.

**Work-items:**
```
proposed ─┬─→ not-started ─→ in-progress ─→ in-review ─→ done
          │                       ⇅              │
          │                    blocked      (back to in-progress
          │                                   if changes-requested)
          └─→ abandoned   (reachable from ANY state above)
```
`blocked` is temporary (still owned, waiting on something, returns to
`in-progress`). `in-review` means the author is done and a reviewer is
looking (see §5 for the finding-level detail underneath this status).
`abandoned` is terminal, reachable from any state — a rejected Proposal is
simply `abandoned`, not a separate word. A promoted Proposal gets
`status: done` (its job — leading to a decision — is finished), not a new
"accepted" word; `promoted:`/`originated_from:` carry the lineage.

**Artifacts:**
```
draft → approved / current → superseded
```

**Terminal statuses** (only these are archivable): `done`, `abandoned`, `superseded`.

## 7. Scenario tags

`scenario:` distinguishes the kind of work independent of where it lives — a
bug fix and a performance task are both `TASK-xx.md` in the same place;
`scenario` is what tells them apart.

`feature`, `enhancement`, `bug`, `refactor`, `spike`, `change-request`,
`performance`, `docs`, `config`, `migration`, `hotfix`, `rollback`,
`deprecation`, `compliance`, `dependency-upgrade`, `research`.

## 8. Frontmatter schema

```yaml
---
id: TASK-01-artifact-store-interface
type: task                    # see §1
kind: work-item                # see §3 - derived from type, don't set independently
status: done                   # see §6, matching kind's vocabulary
parent: STORY-01-payment-backend
owner: YourName
updated: 2026-08-18
scenario: feature              # situational - see §7
project: my_project             # situational - only once cross-project id collisions are possible
mvp: true                      # situational - MVP scope marker for Epic/Story
related: ADHOC-some-other-item        # situational - non-tree cross-reference
originated_from: PROPOSAL-xx    # situational - spawning lineage (proposal -> epic)
supersedes: TASK-04-old-approach # situational - change-request lineage
reverts: TASK-09-broken-change  # situational - rollback lineage
promoted: TASK-07-...            # situational - row-to-file promotion marker
---
```

`validate` checks: `type` known, `status` valid for that type's `kind`,
`id` matches filename and prefix matches `type`, and every
`parent`/`related`/`originated_from`/`supersedes`/`reverts` resolves to a
real id. `review.md` rows are checked the same way against their own
status vocabulary (§5).

## 9. What the tool will never do

- Enforce writing quality — it validates that a field exists, not that the
  content is actually resumable by someone else later.
- Provide arbitrary querying (no joins/aggregations) — `query`'s filter
  flags are the ceiling.
- Sync automatically with real Jira/ADO (not built; the plugin architecture
  leaves room for it later).
- Migrate old, pre-existing docs into this convention automatically.
