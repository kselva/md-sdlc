"""
handover - print a self-contained context pack for one Story, for pasting
into an AI coding agent.

Motivation (PROPOSAL-0.3.0 section 1.2 #3): "agents were over-fed context"
- handover meant pasting requirements_raw.md and large slices of the EPIC
  tree. This command emits ONLY what THIS Story needs: the fixed
  behavioural contract (AI-RULES.md), the Story body, its open task rows,
  its touches: list, its linked artifacts, and any open review findings.
  No siblings, no parent EPIC body, no requirements_raw.md.

Reuses core/repo.py traversal and validate's gate; no filesystem writes.
"""
import argparse
import sys

from core.repo import AiDocsRepo
from core.vocab import kind_for_type
from plugins.base_plugin import BaseCommand
from plugins.validate.plugin import Command as ValidateCommand

_AI_RULES_RELPATH = "AI-RULES.md"


class Command(BaseCommand):
    name = "handover"
    description = "Print a one-Story context pack (AI-RULES + story + tasks + touches + links) for an agent"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("story_id", help="Story id to hand over, e.g. STORY-01-payment-backend")
        parser.add_argument(
            "--full", action="store_true",
            help="Inline the body of each linked artifact (default: id + path only)",
        )
        parser.add_argument(
            "--strict", action="store_true",
            help="Refuse to emit the pack (exit 1) if `validate` currently fails for the project",
        )

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        story = repo.find(args.story_id)
        if story is None or story.type != "story":
            print(f"ERROR: '{args.story_id}' is not a known story")
            sys.exit(1)

        errors, _warnings = ValidateCommand().collect(repo)
        if errors and args.strict:
            print(
                f"ERROR: validate reports {len(errors)} error(s) - refusing to build a "
                f"handover pack with --strict. Run `md_sdlc validate` and fix them first."
            )
            sys.exit(1)

        blocks: list[str] = []
        blocks.append(f"BRANCH: feat/{story.id}")

        if errors:
            blocks.append(
                "!!! WARNING: `md_sdlc validate` currently reports "
                f"{len(errors)} error(s) for this project. This pack may be "
                "built on an inconsistent tree - run `md_sdlc validate` first."
            )

        blocks.append(self._ai_rules_block(repo))
        blocks.append(self._story_block(story))
        blocks.append(self._open_tasks_block(repo, story))
        blocks.append(self._touches_block(story))
        blocks.append(self._linked_artifacts_block(repo, story, full=args.full))
        blocks.append(self._open_findings_block(repo, story))

        sys.stdout.buffer.write(("\n\n".join(blocks) + "\n").encode("utf-8"))

    # -- blocks --------------------------------------------------------

    def _ai_rules_block(self, repo: AiDocsRepo) -> str:
        rules_path = repo.root / _AI_RULES_RELPATH
        if rules_path.exists():
            body = rules_path.read_text(encoding="utf-8").strip()
            return f"--- AI-RULES.md (project) ---\n{body}"
        return (
            "--- AI-RULES.md (project) ---\n"
            "(none - create ai-docs/AI-RULES.md from the `md_sdlc init` template "
            "so every agent gets the same behavioural contract)"
        )

    def _story_block(self, story) -> str:
        title = _first_heading(story.body) or story.id
        fm_lines = [
            f"id: {story.id}",
            f"title: {title}",
            f"status: {story.status}",
            f"stability: {story.stability or '(unset)'}",
        ]
        if story.touches:
            fm_lines.append("touches: " + ", ".join(story.touches))
        body = story.body.strip()
        return "--- STORY ---\n" + "\n".join(fm_lines) + "\n\n" + body

    def _open_tasks_block(self, repo: AiDocsRepo, story) -> str:
        rows = [r for r in repo.task_rows(story.id) if r.status not in ("done", "abandoned")]
        if not rows:
            return "--- OPEN TASKS ---\n(none)"
        lines = ["--- OPEN TASKS ---", "| id | status | scenario | summary |", "|----|--------|----------|---------|"]
        for r in rows:
            lines.append(f"| {r.id} | {r.status} | {r.scenario or '-'} | {r.summary} |")
        return "\n".join(lines)

    def _touches_block(self, story) -> str:
        if not story.touches:
            return (
                "--- TOUCHES (edit only these) ---\n"
                "(none declared - add a `touches:` list to story.md if this Story "
                "depends on specific files, so overlap with other agents is visible)"
            )
        lines = ["--- TOUCHES (edit only these) ---"]
        lines += [f"- {p}" for p in story.touches]
        return "\n".join(lines)

    def _linked_artifacts_block(self, repo: AiDocsRepo, story, full: bool) -> str:
        link_ids: list[str] = []
        for field_name in ("related", "originated_from", "supersedes", "reverts"):
            val = getattr(story, field_name, None)
            if val:
                link_ids.append(val)

        artifacts = []
        for lid in link_ids:
            target = repo.find(lid)
            if target is None:
                continue
            if kind_for_type(target.type or "") == "artifact":
                artifacts.append(target)

        if not artifacts:
            return (
                "--- LINKED ARTIFACTS ---\n"
                "(none - if this Story depends on a rule in nfr.md / requirements "
                "sections, add a `related:` link so it travels with the handover)"
            )

        lines = ["--- LINKED ARTIFACTS ---"]
        for a in artifacts:
            rel = a.path.relative_to(repo.root)
            lines.append(f"- {a.id}  ({rel})")
            if full:
                lines.append("")
                lines.append(a.body.strip())
                lines.append("")
        return "\n".join(lines)

    def _open_findings_block(self, repo: AiDocsRepo, story) -> str:
        rows = [r for r in repo.review_rows(story.id) if r.status in ("open", "changes-requested")]
        if not rows:
            return "--- OPEN REVIEW FINDINGS ---\n(none)"
        lines = [
            "--- OPEN REVIEW FINDINGS ---",
            "| id | severity | status | summary | reported_by |",
            "|----|----------|--------|---------|-------------|",
        ]
        for r in rows:
            lines.append(
                f"| {r.id} | {r.severity or '-'} | {r.status} | {r.summary} | {r.reported_by or '-'} |"
            )
        return "\n".join(lines)


def _first_heading(body: str) -> str | None:
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()
    return None
