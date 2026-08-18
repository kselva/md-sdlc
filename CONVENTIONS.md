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

## 5. Status vocabulary

Two vocabularies, kept separate because the same word means different things
for a unit of work versus a reference document.

**Work-items:**
```
proposed ─┬─→ not-started ─→ in-progress ─⇄ blocked ─→ done
          └─→ abandoned   (reachable from ANY state above)
```
`blocked` is temporary (still owned, waiting on something, returns to
`in-progress`). `abandoned` is terminal, reachable from any state — a
rejected Proposal is simply `abandoned`, not a separate word. A promoted
Proposal gets `status: done` (its job — leading to a decision — is finished),
not a new "accepted" word; `promoted:`/`originated_from:` carry the lineage.

**Artifacts:**
```
draft → approved / current → superseded
```

**Terminal statuses** (only these are archivable): `done`, `abandoned`, `superseded`.

## 6. Scenario tags

`scenario:` distinguishes the kind of work independent of where it lives — a
bug fix and a performance task are both `TASK-xx.md` in the same place;
`scenario` is what tells them apart.

`feature`, `enhancement`, `bug`, `refactor`, `spike`, `change-request`,
`performance`, `docs`, `config`, `migration`, `hotfix`, `rollback`,
`deprecation`, `compliance`, `dependency-upgrade`, `research`.

## 7. Frontmatter schema

```yaml
---
id: TASK-01-artifact-store-interface
type: task                    # see §1
kind: work-item                # see §3 - derived from type, don't set independently
status: done                   # see §5, matching kind's vocabulary
parent: STORY-01-payment-backend
owner: YourName
updated: 2026-08-18
scenario: feature              # situational - see §6
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
real id.

## 8. What the tool will never do

- Enforce writing quality — it validates that a field exists, not that the
  content is actually resumable by someone else later.
- Provide arbitrary querying (no joins/aggregations) — `query`'s filter
  flags are the ceiling.
- Sync automatically with real Jira/ADO (not built; the plugin architecture
  leaves room for it later).
- Migrate old, pre-existing docs into this convention automatically.
