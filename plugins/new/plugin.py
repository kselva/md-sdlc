"""
new - scaffold a Proposal/Epic/Story/Task/Adhoc/Experiment file from a template.

Design doc reference: SDLC_Tracking_System_Design.md section 10.4 (#4),
Implementation plan section 5.4.

0.4.0: in short layout (id_style: short) ids and paths come from
core.layout, an epic/story also gets an empty tasks.md and log.md, and
tasks are rows (`item add`), not files.
"""
import argparse
import datetime
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from core import layout
from core.repo import AiDocsRepo, today_date
from core.vocab import ID_PREFIXES, TERMINAL_STATUSES, slugify
from plugins.base_plugin import BaseCommand

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_NO_PARENT_TYPES = {"proposal", "adhoc", "epic"}
_OPTIONAL_PARENT_TYPES = {"experiment"}
_SEQUENCED_TYPES = {"story", "task"}


class Command(BaseCommand):
    name = "new"
    description = "Create a new Proposal/Epic/Story/Task/Adhoc/Experiment file from a template"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("type", choices=sorted(ID_PREFIXES.keys()), help="Type of item to create")
        parser.add_argument("--title", required=True, help="Title / summary")
        parser.add_argument("--parent", default=None, help="Parent id (required for story/task, optional otherwise)")
        parser.add_argument("--owner", default=None, help="Owner name")
        parser.add_argument("--scenario", default=None, help="Scenario tag, e.g. feature, bug, spike")
        parser.add_argument("--originated-from", default=None, help="Proposal id this epic originated from")
        parser.add_argument("--code", default=None,
                            help="Short layout: epic code (required, e.g. PAY1) or story code (optional, e.g. A)")
        parser.add_argument("--question", default=None, help="Experiment: the one question it answers")

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        type_ = args.type
        prefix = ID_PREFIXES[type_]
        slug = slugify(args.title)
        updated = datetime.date.today().isoformat()
        owner = args.owner or "unassigned"

        parent_item = None
        needs_parent = type_ not in _NO_PARENT_TYPES and type_ not in _OPTIONAL_PARENT_TYPES
        if needs_parent or (type_ in _OPTIONAL_PARENT_TYPES and args.parent):
            if not args.parent:
                print(f"ERROR: --parent is required for type '{type_}'")
                sys.exit(1)
            parent_item = repo.find(args.parent)
            if parent_item is None:
                print(f"ERROR: parent '{args.parent}' does not exist")
                sys.exit(1)
            if parent_item.status in TERMINAL_STATUSES:
                print(f"ERROR: parent '{args.parent}' has terminal status '{parent_item.status}', refusing to add a child")
                sys.exit(1)

        if type_ == "experiment" and not args.question:
            print("ERROR: --question is required for an experiment")
            sys.exit(1)

        if layout.is_short(repo):
            self._run_short(repo, args, parent_item, owner)
            return

        if type_ in _SEQUENCED_TYPES:
            seq = repo.next_sequence(args.parent, type_)
            item_id = f"{prefix}-{seq:02d}-{slug}"
        elif type_ == "epic":
            item_id = f"{prefix}-{slug}"
        else:
            item_id = f"{prefix}-{slug}"

        target_path = self._resolve_path(repo, type_, item_id, parent_item)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))
        template = env.get_template(f"{type_}.md.j2")
        content = template.render(
            id=item_id,
            title=args.title,
            owner=owner,
            updated=updated,
            scenario=args.scenario or "feature",
            parent=args.parent,
            originated_from=args.originated_from,
            question=args.question,
        )
        target_path.write_text(content, encoding="utf-8")
        print(f"Created {item_id} -> {target_path.relative_to(repo.root)}")

    def _resolve_path(self, repo: AiDocsRepo, type_: str, item_id: str, parent_item) -> Path:
        if type_ == "proposal":
            return repo.root / f"{item_id}.md"
        if type_ == "adhoc":
            return repo.root / f"{item_id}.md"
        if type_ == "epic":
            return repo.root / item_id / "epic.md"
        if type_ == "story":
            epic_dir = parent_item.path.parent
            return epic_dir / item_id / "story.md"
        if type_ == "task":
            story_dir = parent_item.path.parent
            return story_dir / f"{item_id}.md"
        if type_ == "experiment":
            folder = parent_item.path.parent if parent_item is not None else repo.root
            return folder / f"{item_id}.md"
        raise ValueError(f"Unhandled type: {type_}")

    # -- short layout (0.4.0) ----------------------------------------------

    def _run_short(self, repo: AiDocsRepo, args: argparse.Namespace, parent_item, owner: str) -> None:
        type_ = args.type
        if type_ == "task":
            print("ERROR: in short layout tasks are rows - use: item add <story-or-epic-id> \"text\"")
            sys.exit(1)
        if type_ == "story" and parent_item.type != "epic":
            print(f"ERROR: a story's parent must be an epic, '{parent_item.id}' is a {parent_item.type}")
            sys.exit(1)

        if type_ == "epic":
            problem = layout.check_code(args.code)
            if problem:
                print(f"ERROR: {problem}")
                sys.exit(1)
            item_id = layout.epic_id(args.code)
        elif type_ == "story":
            if args.code and layout.check_code(args.code):
                print(f"ERROR: {layout.check_code(args.code)}")
                sys.exit(1)
            item_id = layout.story_id(repo, parent_item, args.code)
        elif type_ == "experiment":
            item_id = layout.experiment_id(repo, parent_item, args.title)
        else:
            item_id = layout.plain_id(type_, args.title)

        if repo.find(item_id) is not None:
            print(f"ERROR: id '{item_id}' already exists ({repo.find(item_id).path.relative_to(repo.root)})")
            sys.exit(1)

        target_path = layout.item_path(repo, type_, item_id, args.title, parent_item)
        if target_path.exists():
            print(f"ERROR: {target_path.relative_to(repo.root)} already exists")
            sys.exit(1)

        meta = {"id": item_id, "type": type_, "kind": "work-item",
                "status": "proposed" if type_ == "proposal" else "not-started"}
        if parent_item is not None:
            meta["parent"] = parent_item.id
        meta.update({"title": args.title, "owner": owner, "updated": today_date(),
                     "scenario": args.scenario or "feature"})
        if args.originated_from:
            meta["originated_from"] = args.originated_from
        if type_ in ("epic", "story"):
            meta["next"] = ""
        if type_ == "experiment":
            meta.update({"question": args.question, "verdict": "open"})
        repo.write_item(target_path, meta, _short_body(type_, args.title, args.question))

        if type_ in ("epic", "story"):
            repo.init_item_folder(item_id, target_path.parent)
        print(f"Created {item_id} -> {target_path.relative_to(repo.root)}")


_SHORT_BODIES = {
    "epic": "## Goal\n\n## Steps\nOne folder per step. Open items: tasks.md. Notes: log.md.\n",
    "story": "## Plan\n\n## Done when\n",
    "experiment": "## Question\n{question}\n\n## Method\n\n## Result\n",
    "proposal": "## Idea\n\n## Why\n",
    "adhoc": "",
}


def _short_body(type_: str, title: str, question: str | None) -> str:
    return f"\n# {title}\n\n" + _SHORT_BODIES[type_].format(question=question or "")
