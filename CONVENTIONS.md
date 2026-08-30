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
stability: exploring            # situational (epic/story) - see §10
touches:                        # situational (story) - see §10
  - code/apps/api/src/salary/cycles/
  - code/packages/types/src/salary-cycle.ts
---
```

`validate` checks: `type` known, `status` valid for that type's `kind`,
`stability` (if set) is one of `exploring`/`settled`/`locked`, `id`
matches filename and prefix matches `type`, and every
`parent`/`related`/`originated_from`/`supersedes`/`reverts` resolves to a
real id. `review.md` rows are checked the same way against their own
status vocabulary (§5). `touches:` is **not** checked against the
filesystem - a Story may legitimately create new paths.

## 9. `.sdlc/config.yml` keys

Created by `init`, walked up to like `.git/`. Never hand-edit `name` /
`project_prefix` / `tool_version`. Optional keys a project may add:

```yaml
code_root: ../                       # tree that touches: globs resolve against
                                     #   (default: the folder containing ai-docs/)
test_file_globs:                     # filenames validate's test gate treats as
  - "*.spec.ts"                      #   assertion/spec tests (defaults shipped)
  - "*.test.ts"
  - "*_test.py"
smoke_test_glob: "*.smoke.spec.ts"   # the ONE test an `exploring` Story may have
```

## 10. Stability and the test gate

`stability:` is a situational field on `epic` and `story`. It is **not** a
status - `status` is where the item sits in its lifecycle, `stability` is
whether the customer has frozen the behaviour yet. It exists because
writing deep tests against behaviour the customer is still changing means
throwing that test work away on every change.

| Value | Meaning | Docs | Tests allowed |
|---|---|---|---|
| `exploring` | customer still deciding behaviour | one-paragraph note / spec | smoke test only |
| `settled` | customer signed off on behaviour | short frozen spec | assertion / golden-file tests |
| `locked` | shipped, in user testing | spec frozen | tests frozen |

**Ceremony limits while `exploring`** (a Story marked `exploring` is meant
to be cheap to iterate):

- Skip `TASK-xx.md` files - keep tasks as rows in `tasks.md`. `validate`
  WARNS on a promoted Task file under an `exploring` Story.
- Skip assertion tests - one smoke test only (output parses, count > 0).
  `validate` ERRORS if a file matching `test_file_globs` (see §9) exists
  under the Story's `touches:` paths; a single `smoke_test_glob` match is
  exempt. This check lists directory entries only - it never reads or runs
  a test.
- Don't ship it. `validate` WARNS on `status: done` while `exploring`, and
  the project rule is "no Story enters user testing while `exploring`".

**`touches:`** is an advisory list of repo-relative path globs a Story
expects to edit, resolved against `code_root` (§9). Its jobs:

- `validate` emits a WARNING when two Stories that are both
  `in-progress` / `in-review` have overlapping `touches:` prefixes - a
  prompt to sequence them, never an error.
- `md_sdlc query --active` lists every active Story with its branch and
  `touches:` - run it before handing out a new Story to check for overlap
  by eye.
- `md_sdlc handover <story-id>` prints the `touches:` list into the agent
  pack as "edit only these".

`touches:` is only as honest as the person who fills it in - the tool does
not and will not verify it against the filesystem.

## 11. Sample-data / golden-file development

For a feature whose behaviour the customer has not frozen, verifying
against a real data sample + a hand-checked expected-output file beats
writing an assertion spec that gets rewritten weekly.

- Fixtures live in `ai-docs/samples/` (sibling to `hist/`) **or** in the
  host repo's own test tree, `related:`-linked from the Story.
- Every fixture carries `pulled_on:` and `source:` metadata.
- While the Story is `exploring`, the expected-output file is **editable**
  and is the working reference (diff + eyeball). When the Story goes
  `settled`, that file is **frozen** and one thin test asserts the calc
  output deep-equals it.
- Production data must be anonymised **at pull time** - never store
  un-anonymised customer data in the repo.

## 12. AI agent behavioural contract

`ai-docs/AI-RULES.md` (one per project, ~30 lines, behaviour rules only -
project *facts* stay in the host's own `CLAUDE.md` / rules file) is created
by `md_sdlc init` from a shipped template. `md_sdlc handover` prepends it
to every context pack, so no agent is handed work without it. Edit it for
your project; keep it short.

## 13. What the tool will never do

- Enforce writing quality — it validates that a field exists, not that the
  content is actually resumable by someone else later.
- Provide arbitrary querying (no joins/aggregations) — `query`'s filter
  flags and `stats`' status matrix / grouped counts are the ceiling.
- Sync automatically with real Jira/ADO (not built; the plugin architecture
  leaves room for it later).
- Migrate old, pre-existing docs into this convention automatically.
