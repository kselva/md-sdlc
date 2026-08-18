"""
init - mark the current directory as an SDLC-tracked project.

Mirrors `npm init`/`git init`: creates .sdlc/config.yml here, plus the base
skeleton (hist/) so `archive` has somewhere to move things later. Does not
require an existing project (special-cased in sdlc_tool.py's dispatch) -
this IS the command that creates one.
"""
import argparse
import sys
from pathlib import Path

from core.profile import init_marker
from plugins.base_plugin import BaseCommand


class Command(BaseCommand):
    name = "init"
    description = "Initialize the current folder as an SDLC-tracked project (creates .sdlc/config.yml)"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--name", required=True, help="Human-readable project name")
        parser.add_argument("--prefix", required=True, help="Short project prefix, e.g. STO, used for future cross-project disambiguation")
        parser.add_argument("--path", default=".", help="Folder to initialize (default: current directory)")

    def run(self, repo, args: argparse.Namespace) -> None:
        target = Path(args.path).resolve()
        target.mkdir(parents=True, exist_ok=True)

        try:
            config_path = init_marker(target, args.name, args.prefix)
        except FileExistsError as exc:
            print(f"ERROR: {exc}")
            sys.exit(1)

        (target / "hist").mkdir(exist_ok=True)

        print(f"Initialized '{args.name}' ({args.prefix}) at {target}")
        print(f"  marker: {config_path.relative_to(target)}")
        print(f"  created: hist/")
        print(f"Run 'python sdlc_tool.py new proposal --title \"...\"' to get started.")
