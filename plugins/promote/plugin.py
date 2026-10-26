"""
promote - row -> own file, or Proposal -> Epic (on acceptance).

Design doc reference: SDLC_Tracking_System_Design.md section 10.4 (#5),
section 7 (acceptance is a spawning event), Implementation plan section 5.5,
section 7 decision #2 (accepted Proposal reuses status: done).

0.4.0: the Proposal header is updated in place (extra fields kept); in
short layout the new Epic needs --code and gets tasks.md/log.md, and rows
stay rows (--to-file is classic only).
"""
import argparse
import datetime
import sys

from core import frontmatter as fmwrite
from core import layout
from core.repo import AiDocsRepo
from core.vocab import slugify
from plugins.base_plugin import BaseCommand


class Command(BaseCommand):
    name = "promote"
    description = "Promote a tasks.md row to its own file, or a Proposal to an Epic"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("id", help="Task row id (e.g. TASK-01) or Proposal id")
        parser.add_argument("--to-file", action="store_true", help="Promote a tasks.md row to its own TASK-xx.md file")
        parser.add_argument("--to-epic", action="store_true", help="Promote an accepted Proposal to a new Epic")
        parser.add_argument("--story", default=None, help="Story id the row belongs to (required with --to-file)")
        parser.add_argument("--code", default=None, help="Short layout: code for the new Epic, e.g. PAY2")

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        if args.to_file:
            self._row_to_file(repo, args)
        elif args.to_epic:
            self._proposal_to_epic(repo, args)
        else:
            print("ERROR: specify --to-file or --to-epic")
            sys.exit(1)

    def _row_to_file(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        if layout.is_short(repo):
            print("ERROR: in short layout open items stay rows - for bigger work use 'new story' or 'new experiment'")
            sys.exit(1)
        if not args.story:
            print("ERROR: --story is required with --to-file")
            sys.exit(1)
        rows = repo.task_rows(args.story)
        row = next((r for r in rows if r.id == args.id), None)
        if row is None:
            print(f"ERROR: row '{args.id}' not found in {args.story}/tasks.md")
            sys.exit(1)

        story = repo.find(args.story)
        seq = repo.next_sequence(args.story, "task")
        slug = slugify(row.summary) or "promoted-task"
        new_id = f"TASK-{seq:02d}-{slug}"
        target_path = story.path.parent / f"{new_id}.md"

        metadata = {
            "id": new_id,
            "type": "task",
            "kind": "work-item",
            "status": row.status,
            "parent": args.story,
            "owner": row.owner or "unassigned",
            "updated": datetime.date.today(),
            "scenario": row.scenario or "feature",
            "promoted": f"was row {row.id} in tasks.md",
        }
        fmwrite.write(target_path, metadata, f"\n# {row.summary}\n\nPromoted from a tasks.md row.\n")

        self._remove_row_leave_pointer(story.path.parent / "tasks.md", row, new_id)
        print(f"Promoted {row.id} -> {new_id} at {target_path.relative_to(repo.root)}")

    def _remove_row_leave_pointer(self, tasks_md, row, new_id: str) -> None:
        text = tasks_md.read_text(encoding="utf-8")
        lines = text.splitlines()
        out = [line for line in lines if not (line.strip().startswith(f"| {row.id} "))]
        out.append("")
        out.append(f"_{row.id} promoted to its own file: [{new_id}.md]({new_id}.md)_")
        tasks_md.write_text("\n".join(out) + "\n", encoding="utf-8")

    def _proposal_to_epic(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        proposal = repo.find(args.id)
        if proposal is None or proposal.type != "proposal":
            print(f"ERROR: '{args.id}' is not a known proposal")
            sys.exit(1)

        title = proposal.display_title
        if layout.is_short(repo):
            problem = layout.check_code(args.code)
            if problem:
                print(f"ERROR: {problem}")
                sys.exit(1)
            epic_id = layout.epic_id(args.code)
            target_path = layout.item_path(repo, "epic", epic_id, title, None)
        else:
            epic_id = f"EPIC-{slugify(title)}"
            target_path = repo.root / epic_id / "epic.md"
        if repo.find(epic_id) is not None:
            print(f"ERROR: id '{epic_id}' already exists")
            sys.exit(1)

        metadata = {
            "id": epic_id,
            "type": "epic",
            "kind": "work-item",
            "status": "not-started",
            "owner": proposal.owner or "unassigned",
            "updated": datetime.date.today(),
            "originated_from": proposal.id,
            "mvp": False,
        }
        if layout.is_short(repo):
            metadata["title"] = title
        repo.write_item(target_path, metadata, f"\n# {title}\n\n{proposal.body.strip()}\n")
        if layout.is_short(repo):
            repo.init_item_folder(epic_id, target_path.parent)

        repo.update_header(proposal, {"status": "done", "promoted": epic_id})

        print(f"Promoted {proposal.id} -> {epic_id} at {target_path.relative_to(repo.root)}")
