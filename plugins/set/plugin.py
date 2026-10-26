"""
set - change header fields of an item in place (0.4.0).

Only the named fields change; every other field, the key order and the body
stay as they are. updated is set to today. An empty value ("") removes a
field, e.g. --waits-on "" once the wait is over.
"""
import argparse
import sys

from core.repo import AiDocsRepo
from core.vocab import is_valid_status, is_valid_verdict
from plugins.base_plugin import BaseCommand

_FIELDS = ("status", "next", "waits_on", "deployed", "result", "verdict", "title", "question", "owner")


class Command(BaseCommand):
    name = "set"
    description = "Change header fields of an item (status, next, waits-on, deployed, result, verdict, ...)"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("id", help="Item id")
        parser.add_argument("--status", default=None)
        parser.add_argument("--next", default=None, help="One line: what happens next")
        parser.add_argument("--waits-on", dest="waits_on", default=None,
                            help="Who or what it waits on (the project's decision_waits word = owner decision)")
        parser.add_argument("--deployed", default=None, help="What is on site and when, e.g. 'v1.2 2026-03-04'")
        parser.add_argument("--result", default=None, help="Experiment result, one line")
        parser.add_argument("--verdict", default=None, help="Experiment verdict: open / yes / no / partly")
        parser.add_argument("--title", default=None)
        parser.add_argument("--question", default=None)
        parser.add_argument("--owner", default=None)

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        item = repo.find(args.id)
        if item is None:
            print(f"ERROR: '{args.id}' not found")
            sys.exit(1)

        changes = {f: getattr(args, f) for f in _FIELDS if getattr(args, f) is not None}
        if not changes:
            print("ERROR: nothing to set - give at least one field, e.g. --status done")
            sys.exit(1)
        if "status" in changes and not is_valid_status(item.type, changes["status"]):
            print(f"ERROR: '{changes['status']}' is not a valid status for type '{item.type}'")
            sys.exit(1)
        if changes.get("verdict") and not is_valid_verdict(changes["verdict"]):
            print(f"ERROR: verdict must be open, yes, no or partly - got '{changes['verdict']}'")
            sys.exit(1)

        changes = {k: (v if v != "" else None) for k, v in changes.items()}
        repo.update_header(item, changes)
        shown = ", ".join(f"{k}={'(removed)' if v is None else v}" for k, v in changes.items())
        print(f"Updated {item.id}: {shown}")
