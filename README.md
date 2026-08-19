# md-sdlc

CLI for tracking Epics/Stories/Tasks/Proposals/Ad hoc work as markdown files with
frontmatter, across one or more project `ai-docs/`-style trees. A file-based,
lightweight alternative to a JIRA board.

## How it works

Every tracked file has a YAML frontmatter header (`id`, `type`, `kind`, `status`,
`parent`, ...). The tool never guesses — it reads and validates these fields, and
generates rollup views (`backlog.md`) from them. Nothing is ever hand-edited by the
tool except through the commands below; `backlog.md` files are always fully
regenerated, never merged.

## Setup

**Option A — compiled binary (recommended, no Python required):**

Build once, then use `dist\md_sdlc.exe` directly, or add its folder to `PATH`
so `md_sdlc` works from any shell without a path prefix.

**Option B — run from source (for development):**

```bash
pip install python-frontmatter pyyaml jinja2
python sdlc_tool.py validate
```

**Building the exe:**

```bash
pip install pyinstaller
python -m PyInstaller md_sdlc.spec --distpath dist --workpath build
```

## Initializing a project

Targeting is git-style: no central registry of project paths. Each project marks
itself with a `.sdlc/config.yml` inside its own tracked folder (e.g. `ai-docs/`),
and every command auto-detects the nearest one by walking up from the current
directory — same as `git` finding `.git/`.

```bash
cd /path/to/your-project/ai-docs
md_sdlc init --name "Your Project" --prefix YP
```

This creates `ai-docs/.sdlc/config.yml` and `ai-docs/hist/`. Nothing else is
touched. Run any other command from inside (or under) that folder afterward —
no flags needed to say which project you mean:

```bash
cd /path/to/your-project/ai-docs
md_sdlc validate
```

Running a command outside any initialized project fails clearly:

```
ERROR - not initialized - no .sdlc/ found in this folder or any parent.
  Run 'md_sdlc init' inside your project's folder first.
```

Adding a second, third, ... project to track is just running `init` inside
that project's own folder too — no code change, no shared config file to edit
or keep in sync.

(Examples below use `md_sdlc`; substitute `python sdlc_tool.py` if running from source.)

## Commands

### init

```bash
md_sdlc init --name "Project Name" --prefix ABC [--path .]
```

### conventions

Print the full naming/folder/status/schema rules this tool enforces
(the contents of `CONVENTIONS.md`) — the canonical reference, not a summary.

```bash
md_sdlc conventions
```

### validate

Walk the whole tree, check frontmatter schema, vocabulary, and that every
`parent`/`related`/`originated_from`/`supersedes`/`reverts` link resolves.

```bash
md_sdlc validate
```

### backlog

Regenerate the rollup. No args regenerates the root Epic-level `backlog.md`;
`--epic` regenerates one Epic's own Story+Task level `backlog.md`.

```bash
md_sdlc backlog
md_sdlc backlog --epic EPIC-01-checkout-redesign
```

### query

Filtered counts/listings — the "how many open", "MVP remaining", "stale items"
questions, without opening files by hand.

```bash
md_sdlc query --type task --status in-progress
md_sdlc query --owner YourName --stale-days 14
md_sdlc query --mvp-remaining
```

### new

Scaffold a new item from a template, at the correct nested path, with the next
sequence number computed automatically for Story/Task.

```bash
md_sdlc new proposal --title "Idea for X" --owner YourName
md_sdlc new epic --title "Big Initiative" --originated-from PROPOSAL-idea-for-x
md_sdlc new story --parent EPIC-big-initiative --title "First Slice" --owner YourName
md_sdlc new task --parent STORY-01-first-slice --title "Do the thing" --owner YourName --scenario bug
md_sdlc new adhoc --title "Prod hotfix" --owner YourName --scenario hotfix
```

Refuses to create a child under a parent that doesn't exist or has a terminal
status (`done`/`abandoned`/`superseded`).

### promote

Two promotion paths — acceptance is a spawning event, not just a status change:

```bash
# a tasks.md row outgrew a row - give it its own file
md_sdlc promote TASK-01 --to-file --story STORY-01-first-slice

# a Proposal was accepted - spawn an Epic, link lineage both ways
md_sdlc promote PROPOSAL-idea-for-x --to-epic
```

A promoted Proposal gets `status: done` (its job — leading to a decision — is
finished) rather than a new vocabulary word; the resulting Epic carries
`originated_from:` and the Proposal carries `promoted:`.

### review

Multi-agent (or multi-person) handoff: one agent designs/codes a Story, a
second reviews it and writes findings to `STORY-xx/review.md`, the first
agent fixes and resolves them.

```bash
# reviewer reports a finding
md_sdlc review report --story STORY-01-first-slice \
  --summary "Race condition in retry logic" --severity critical --reported-by agent-2

# author resolves it after fixing
md_sdlc review resolve RVW-01 --story STORY-01-first-slice --status fixed
```

`--status` accepts `fixed`, `wontfix`, or `changes-requested` (sends it back
for another look). Findings use their own status vocabulary (open ->
changes-requested -> fixed/wontfix), separate from task/story status — see
`CONVENTIONS.md` §5. The Story's own status can be `in-review` while its
`review.md` still has open rows.

### archive

Move a terminal-status item to `hist/`. Refuses on any non-terminal status —
no `--force` in Phase 1.

```bash
md_sdlc archive TASK-01-do-the-thing
```

## Architecture

A `BaseCommand` ABC, one plugin per subcommand under `plugins/<name>/plugin.py`.
In dev mode, `plugins/__init__.py` auto-discovers plugins by walking the folder —
dropping in a new plugin folder is the entire integration step. In the compiled
exe, plugin discovery falls back to a fixed import list (`sys.frozen` check),
since a frozen binary has no real `plugins/` directory to walk and PyInstaller's
static analysis can't see dynamically-imported modules — that list must be kept
in sync with `plugins/*/plugin.py` when a plugin is added or removed.

`core/repo.py`'s `AiDocsRepo` is the only class that touches the filesystem;
every plugin goes through it. `core/profile.py` resolves the current project by
walking up for `.sdlc/config.yml` (see "Initializing a project" above).

```
md-sdlc/
  md_sdlc.spec               # PyInstaller build spec (bundles plugins/new/templates as data)
  sdlc_tool.py                # CLI entry point
  core/
    profile.py                 # git-style .sdlc/ marker discovery
    frontmatter.py               # parse/write YAML frontmatter (pure serialization)
    models.py                     # WorkItemFile, TaskRow, ReviewRow dataclasses
    vocab.py                       # fixed type/status/scenario vocabulary + slugify
    repo.py                         # AiDocsRepo - the only filesystem touchpoint
  plugins/
    base_plugin.py                # BaseCommand(ABC)
    validate/ backlog/ query/ new/ promote/ archive/ init/ review/ conventions/
  tests/
    fixtures/                     # committed regression fixtures, incl. one
                                   # deliberate broken-link violation for validate
  dist/
    md_sdlc.exe                    # built binary (gitignored by default - see .gitignore)
```

## Non-goals (Phase 1)

- No Jira/ADO sync (the plugin architecture leaves room for a future `jira_sync/`
  plugin, but it isn't built yet)
- No migration of existing docs into this convention — applies going forward only
- No web UI — CLI output only
- No automatic/scheduled archival
- No cross-project aggregation queries (each project is targeted independently)
