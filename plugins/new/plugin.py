"""
new - scaffold a Proposal/Epic/Story/Task/Adhoc file from a template.

Design doc reference: SDLC_Tracking_System_Design.md section 10.4 (#4),
Implementation plan section 5.4.
"""
import argparse
import datetime
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from core.repo import AiDocsRepo
from core.vocab import ID_PREFIXES, TERMINAL_STATUSES, slugify
from plugins.base_plugin import BaseCommand

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_NO_PARENT_TYPES = {"proposal", "adhoc", "epic"}
_SEQUENCED_TYPES = {"story", "task"}


class Command(BaseCommand):
    name = "new"
    description = "Create a new Proposal/Epic/Story/Task/Adhoc file from a template"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("type", choices=sorted(ID_PREFIXES.keys()), help="Type of item to create")
        parser.add_argument("--title", required=True, help="Title / summary")
        parser.add_argument("--parent", default=None, help="Parent id (required for story/task, optional otherwise)")
        parser.add_argument("--owner", default=None, help="Owner name")
        parser.add_argument("--scenario", default=None, help="Scenario tag, e.g. feature, bug, spike")
        parser.add_argument("--originated-from", default=None, help="Proposal id this epic originated from")

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        type_ = args.type
        prefix = ID_PREFIXES[type_]
        slug = slugify(args.title)
        updated = datetime.date.today().isoformat()
        owner = args.owner or "unassigned"

        parent_item = None
        if type_ not in _NO_PARENT_TYPES:
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
        raise ValueError(f"Unhandled type: {type_}")
