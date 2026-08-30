# Proposal - md-sdlc 0.3.0: stability gate, agent handover pack, collision guards

Status: current
Author: kselva
Date: 2026-08-30
Target version: 0.3.0

This document is the requirement statement and proposed solution for the
next md-sdlc release. It exists because the host project (a payroll web
app) adopted md-sdlc 0.2.0 and hit a wall that the tool, as built, does
not address.

---

## 1. Problem statement - what went wrong in real use

### 1.1 Context

The host project is a payroll web app built largely by AI coding agents,
with one or two people directing them. Requirements come from a customer
(a payroll company) who does not freeze behaviour up front - they keep
asking for changes until they see working output and settle.

md-sdlc 0.2.0 was introduced to carry user requirements through to tech
design and hand structured work to the agents:

```
Discussion -> Design discussion with AI -> Tech design -> EPICs ->
Stories -> Tasks -> AI handover -> Review for completion ->
Review changes -> Complete development -> User testing -> User feedback
```

### 1.2 The failure

Development slowed to a crawl. Root causes, in order of cost:

1. **Tests were written early and deep, against unfrozen behaviour.**
   Every customer customization changed behaviour, which forced a spec
   rewrite, a suite run (the API suite is Postgres-backed, ~10 minutes),
   and a fix loop. On a requirement that changed weekly, this was work
   thrown away weekly. Agents visibly "got stuck in the loop" here.

2. **Every small change carried full work-item ceremony.** A one-line
   customer tweak triggered: new STORY/TASK files, frontmatter, `validate`,
   `backlog` regen, a handover doc, `review.md` rows. The process cost per
   change exceeded the change itself.

3. **Agents were over-fed context.** Handover meant pasting
   `requirements_raw.md` and large slices of the EPIC tree. High token
   cost, and the signal (what THIS story needs) was buried.

4. **Multiple agents edited the same files.** Two agents would both edit a
   shared service or a types file with no awareness of each other. The
   clash surfaced late - at the EPIC boundary, because of a
   no-test-run-until-EPIC policy - as a silent broken combination or a
   messy overwrite.

### 1.3 What is explicitly NOT the problem

- md-sdlc's core design (marker discovery, generated rollups, `validate`
  referential integrity, row-tables that graduate to files) is sound and
  is not being changed.
- No external tracker (Jira, Linear, GitHub Projects, spec-kit) solves
  1.2. None of them gate test-writing on requirement stability. This is
  not a "switch tools" problem.

---

## 2. Simulation - good case and negative case

Feature under test: "Salary pay cycles" - units paid on a 10-day cycle
(1-10, 11-20, 21-end), office on 15-day (1-15, 16-end), plus weekly
Mon-Sun with short head/tail cycles. Customer has not frozen it.
Two agents: Agent-A (backend calc), Agent-B (frontend cycle picker).

### 2.1 GOOD case (with the 0.3.0 workflow)

1. Tech design produces a one-page spec. Story created with
   `stability: exploring` and a `touches:` list scoped to
   `code/apps/api/src/salary/cycles/` + one types file.
2. Real production data for one unit / one month is pulled, anonymised
   (names -> `Employee NN`, PF numbers faked), saved as a fixture, with a
   hand-checked `expected-aug2026.json` beside it (not frozen).
3. `md_sdlc handover STORY-01-...` prints: branch name, `AI-RULES.md`
   (30 lines fixed), `story.md`, open task rows, `touches:`, fixture
   link. ~250 lines total. Not `requirements_raw.md`.
4. Agent-A builds the calc. Because `stability: exploring`, it writes
   ONE smoke test (output parses, cycle count > 0) - no assertion spec.
   Verification is: run on fixture, diff against `expected-aug2026.json`,
   eyeball against the factory paper register.
5. Agent-B runs `md_sdlc status --active`, sees Agent-A's `touches:`,
   takes a Story scoped to `code/apps/web/src/features/employee-form/`.
   No overlap. Separate branches. They never touch the same file.
6. Customer changes the rule ("21-31 as one cycle; round cycle pay down").
   Cost: edit `expected-aug2026.json` (data), add one `change-request`
   task row, re-run `handover`, Agent-A edits the boundary + rounding,
   re-diffs against the fixture. **No spec rewrite. No suite run.**
7. Customer signs off. Flip to `stability: settled`. NOW Agent-A writes
   one thin golden-file test (assert calc output deep-equals the frozen
   `expected-aug2026.json`). Story -> in-review -> done ->
   `stability: locked` -> `md_sdlc archive`.

Outcome: 3 requirement changes absorbed with zero suite runs; tests
written once, at the end, against frozen behaviour; two agents parallel
with no collision; every agent got the same 30-line rule sheet.

### 2.2 NEGATIVE cases (discipline skipped, or guardrail catches you)

- **2a - agent writes deep tests on an `exploring` Story.**
  `md_sdlc validate` errors: spec test file present under
  `stability: exploring`. Caught before merge. A 2-hour repeated-rewrite
  bleed becomes a 2-minute catch. Residual risk: only fires if `validate`
  is actually run - mitigate by running it in a pre-merge hook and/or
  having `handover` refuse when `validate` fails.

- **2b - two agents collide anyway.** `status --active` not checked, and
  the second Story's `touches:` was under-declared (missing the shared
  types file). No overlap warning fires. Both edit the file on separate
  branches; the clash surfaces at PR merge as a git conflict - annoying
  (~15 min) but visible and at the right place, versus a silent
  working-tree overwrite found at the EPIC boundary today. Residual risk:
  `touches:` is only as honest as the person who fills it in.

- **2c - handover pack too thin.** A Story depends on a rule in `nfr.md`
  §8 mentioned only in prose, not via a `related:` link. `handover` pulls
  only linked artifacts, so the agent never sees it and rounds the wrong
  way. No guardrail. Mitigate: `handover` prints "Linked artifacts: none -
  add `related:` links if this Story depends on nfr/requirements
  sections." Otherwise this is author discipline `validate` cannot
  enforce.

- **2d - sample data drifts.** The fixture was a one-time pull. Production
  rules later change (new ESI ceiling). Tests pass against a stale
  photograph. Mitigate: `pulled_on:` + `source:` in every fixture; a
  staleness query to flag old fixtures. Genuine limitation of
  fixture-based development.

- **2e - customer never signs off.** Story sits at `exploring` for
  months, tests never written, then ships to user testing untested.
  Mitigate: `query --stability exploring --stale-days 30` surfaces it for
  a human decision, plus a hard rule "no Story enters user testing while
  `exploring`." The workflow makes iterating cheap, which can enable
  indecision - that stays a management problem.

### 2.3 Verdict

The upgrade converts late, invisible, end-of-EPIC failures into early,
cheap, visible ones. It does not remove the need for discipline:
`validate` can enforce the test gate and warn on `touches:` overlap, but
it cannot fill in `touches:`, cannot link the right docs, and cannot make
the customer decide.

---

## 3. Proposed solution - four additions for 0.3.0

All four are small. None changes the core model. Net effect is a
*lighter* process, because `exploring` Stories skip Task files,
`review.md`, and assertion tests entirely.

### 3.1 `stability` field + test gate (the core change)

**Schema (`CONVENTIONS.md` §8):** new situational field on `epic` and
`story`:

```yaml
stability: exploring | settled | locked
```

| Value | Meaning | Docs | Tests allowed |
|---|---|---|---|
| `exploring` | customer still deciding behaviour | one-paragraph note / spec | smoke test only |
| `settled` | customer signed off on behaviour | short frozen spec | assertion / golden-file tests |
| `locked` | shipped, in user testing | spec frozen | tests frozen |

**`validate` rules added:**

1. If a Story with `stability: exploring` has a spec/assertion test file
   in its `touches:` paths (pattern: `*.spec.*`, `*.test.*`, `*_test.*`,
   `test_*.py`), that is an ERROR. A single file matching a configurable
   `smoke_test_glob` is exempt.
2. If a Story is `stability: exploring` and has a promoted `TASK-xx.md`
   file (not just rows), that is a WARNING (ceremony too early).
3. A Story may not have `status` past `in-review` while
   `stability: exploring` - WARNING ("about to ship unfrozen work").

**How the test-file check works without running anything:** `validate`
already walks the tree. Extend it to also stat the `touches:` globs in
the target repo and match filenames against the test-file patterns. It
reads directory entries, never file contents, never executes tests.

**Config:** `.sdlc/config.yml` gains optional keys:

```yaml
test_file_globs: ["*.spec.ts", "*.test.ts", "*_test.py", "*.spec.js"]
smoke_test_glob: "*.smoke.spec.ts"
```

Defaults shipped; projects override.

### 3.2 `md_sdlc handover <story-id>` - the context pack

New plugin `plugins/handover/`. Emits one markdown block to stdout:

```
BRANCH: feat/<story-id>

--- AI-RULES.md (project) ---
<verbatim contents of ai-docs/AI-RULES.md if present>

--- STORY ---
<story.md body, frontmatter stripped to id/title/stability/touches/status>

--- OPEN TASKS ---
<open rows from this Story's tasks.md>

--- TOUCHES (edit only these) ---
<touches: list>

--- LINKED ARTIFACTS ---
<for each related: / originated_from: that is an artifact kind,
 print id + path; if none, print the reminder line from case 2c>

--- OPEN REVIEW FINDINGS ---
<open rows from review.md, if any>
```

Rules:
- Pulls the target Story only. No siblings, no parent EPIC body, no
  `requirements_raw.md`.
- `--full` flag optionally inlines linked artifact bodies (off by
  default - keeps the pack small).
- If `validate` currently fails for the project, `handover` prints a
  warning header (or refuses with `--strict`).
- Reuses `core/repo.py` traversal and `query`'s filters; ~40-60 lines.

### 3.3 `touches:` field + overlap guard + `status --active`

**Schema:** new situational field on `story`:

```yaml
touches:
  - code/apps/api/src/salary/cycles/
  - code/packages/types/src/salary-cycle.ts
```

Free-form repo-relative path globs. Advisory, not validated against the
filesystem (a Story may legitimately create new paths).

**`validate` rule added:** if two Stories are both `status: in-progress`
(or `in-review`) and their `touches:` lists share any path prefix, emit a
WARNING naming both Stories and the overlapping path. Never an error -
sequencing is a human call.

**`query` extension:** `md_sdlc status --active` (or
`query --status in-progress --show branch,touches`) prints one line per
active Story: `id | owner | branch | touches globs`. Run before handing
out a new Story to check for overlap by eye.

### 3.4 `AI-RULES.md` - the fixed behavioural contract

Not a tool feature - a **convention** documented in `CONVENTIONS.md` and a
template shipped by `md_sdlc init`. One file per project at
`ai-docs/AI-RULES.md`, hard cap ~30 lines, behaviour rules only (project
*facts* stay in the host's own `CLAUDE.md` / rules file). `handover`
prepends it to every pack so no agent is handed work without it.

Shipped template body:

```
# AI agent rules - read before touching code

DO
- Work only the Story handed to you. Its files only (see `touches:`).
- Branch: feat/<story-id>. Never commit to main.
- Extend, don't rewrite. Keep existing signatures, exports, response
  shapes, DB columns. New params get defaults.
- Check callers before editing shared code.
- Match surrounding code style. Use the project logger, not console.
- Stop and ask if the Story needs a breaking change.

DON'T
- Don't edit files outside your Story's `touches:` list.
- Don't write assertion tests for a Story marked `stability: exploring` -
  smoke test only.
- Don't run the test suites unless the project says to.
- Don't add per-endpoint audit calls or per-controller response
  formatting if the project centralises them.
- Don't touch env, migrations, or CI config unless the Story says so.
- Don't refactor adjacent code "while you're here".

WHEN DONE
- Summary: what changed, how to verify, risks. 5 lines.
- List any file you touched that wasn't in `touches:`.
```

---

## 4. Sample-data / golden-file development

Adopted by the host project alongside the above. md-sdlc support is minimal:

- New convention: `ai-docs/samples/` (sibling to `hist/`), or fixtures
  live in the host repo's test tree and are `related:`-linked from the
  Story.
- Each fixture carries `pulled_on:` and `source:` metadata.
- While a Story is `exploring`, the "expected output" file is editable and
  is the working reference (diff + eyeball). When the Story goes
  `settled`, that file is frozen and one thin test asserts equality
  against it.
- Optional later: `query --fixtures-stale-days N` to flag old pulls
  (case 2d).

Production data must be anonymised at pull time - never store
un-anonymised customer data in the repo.

---

## 5. Non-goals for 0.3.0

- No enforcement that `touches:` matches reality - advisory only.
- No automatic doc-linking for handover - author must add `related:`.
- No fixture-freshness automation beyond an optional staleness query.
- No change to the core type/status model, rollup generation, or marker
  discovery.
- Still no Jira/ADO sync, no web UI, no cross-project queries.

---

## 6. Delivery split

**md-sdlc repo (this repo), 0.3.0:**
1. `CONVENTIONS.md` - add `stability` and `touches:` to §8; add a new
   section for the test gate and the `exploring` ceremony limits.
2. `plugins/validate/` - the three `stability` rules + the `touches:`
   overlap warning + directory-glob test-file detection.
3. `plugins/handover/` - new plugin (and its entry in
   `plugins/__init__.py` `_FROZEN_PLUGIN_MODULES` AND `md_sdlc.spec`
   `hiddenimports` - the two-place trap from DESIGN_NOTES §7).
4. `plugins/query/` - `--active` view / `show` columns.
5. `plugins/init/` - ship the `AI-RULES.md` template and create it on
   `init`.
6. `.sdlc/config.yml` schema - `test_file_globs`, `smoke_test_glob`.
7. `tests/fixtures/` - add a fixture tree with an `exploring` Story that
   has an illegal spec file, to lock in the new `validate` error.
8. `CHANGELOG.md` - 0.3.0 entry. `core/version.py` bump.

**Host project repo, adoption:**
1. Un-archive `ai-docs/.sdlc/` (restore from `99-archive/`), re-init if
   needed.
2. Add `ai-docs/AI-RULES.md` from the template.
3. Set `stability:` on existing Epics/Stories (best-guess: most are
   `locked`, current work is `exploring`).
4. Write the 3-state model + test gate + sample-data rule into project
   `CLAUDE.md`.
5. Re-point the global Claude instruction back at `md_sdlc conventions`.
6. Establish `code/apps/api/test/fixtures/` (or `ai-docs/samples/`) and
   pull the first anonymised production sample.
