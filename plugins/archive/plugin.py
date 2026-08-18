"""
archive - move a terminal-status item (and its folder, if it has children)
into hist/. Request-only in Phase 1, no automatic/scheduled archival, no
--force override (design doc section 11; implementation plan section 5.6,
section 8).
"""
import argparse
import shutil
import sys

from core.repo import AiDocsRepo
from core.vocab import is_terminal
from plugins.base_plugin import BaseCommand


class Command(BaseCommand):
    name = "archive"
    description = "Move a terminal-status item to hist/"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("id", help="Id of the item to archive")

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        item = repo.find(args.id)
        if item is None:
            print(f"ERROR: '{args.id}' not found")
            sys.exit(1)
        if not is_terminal(item.status):
            print(f"ERROR: '{args.id}' has status '{item.status}', not terminal (done/abandoned/superseded). Refusing to archive.")
            sys.exit(1)

        hist_dir = repo.root / "hist"
        hist_dir.mkdir(exist_ok=True)

        source = item.path.parent if item.path.name in ("epic.md", "story.md") else item.path
        dest = hist_dir / source.relative_to(repo.root)
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists():
            print(f"ERROR: destination already exists in hist/: {dest.relative_to(repo.root)}")
            sys.exit(1)

        shutil.move(str(source), str(dest))
        print(f"Archived {args.id} -> {dest.relative_to(repo.root)}")
