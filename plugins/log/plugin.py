"""
log - add a dated note on top of an item's log.md (0.4.0).

For epic/story folders only (a single-file item keeps notes in its body).
Also sets the item's updated date, so the status view shows it as touched.
"""
import argparse
import sys

from core.repo import AiDocsRepo
from plugins.base_plugin import BaseCommand


class Command(BaseCommand):
    name = "log"
    description = "Add a dated note to an epic/story log.md (newest first)"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("id", help="Epic or story id")
        parser.add_argument("text", help="The note, one line")

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        item = repo.find(args.id)
        if item is None:
            print(f"ERROR: '{args.id}' not found")
            sys.exit(1)
        if not item.is_folder_item:
            print(f"ERROR: '{args.id}' is a single file - log.md is for epic/story folders; write the note in the file")
            sys.exit(1)
        if not args.text.strip():
            print("ERROR: the note is empty")
            sys.exit(1)
        path = repo.append_log(item, args.text)
        repo.update_header(item, {})
        print(f"Logged on {item.id} -> {path.relative_to(repo.root)}")
