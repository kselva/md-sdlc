"""
conventions - print CONVENTIONS.md, the normative naming/status/schema rules.

Requested directly: "folder and naming conventions are our real rules, tool
cli also should give the help for this" - rather than duplicating the rules
into a docstring (which would drift from CONVENTIONS.md), this command
prints the actual file, so there is exactly one place the rules are written.
"""
import argparse
import sys
from pathlib import Path

from plugins.base_plugin import BaseCommand


def _conventions_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "CONVENTIONS.md"
    return Path(__file__).parent.parent.parent / "CONVENTIONS.md"


class Command(BaseCommand):
    name = "conventions"
    description = "Print the naming/folder/status conventions this tool enforces"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        pass

    def run(self, repo, args: argparse.Namespace) -> None:
        path = _conventions_path()
        if not path.exists():
            print(f"ERROR: CONVENTIONS.md not found at {path}")
            sys.exit(1)
        text = path.read_text(encoding="utf-8")
        # stdout may be a non-UTF-8 console codepage (e.g. Windows cp1252),
        # which can't encode the arrow/box-drawing characters in the file
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
