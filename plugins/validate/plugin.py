"""
validate - walk the tree, check schema, vocabulary, and referential integrity.

Design doc reference: SDLC_Tracking_System_Design.md section 10.4 (#1),
Implementation plan section 5.1.
"""
import argparse
import sys

from core.repo import AiDocsRepo
from core.vocab import SCENARIOS, is_valid_status, prefix_for_type
from plugins.base_plugin import BaseCommand


class Command(BaseCommand):
    name = "validate"
    description = "Validate frontmatter schema, vocabulary, and links across the tree"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        pass  # no options for Phase 1 - always validates the whole tree

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        violations = []
        items = repo.all_files()
        known_ids = {item.id for item in items}

        for item in items:
            rel = item.path.relative_to(repo.root)

            if item.kind is None:
                violations.append(f"{rel}: unknown type '{item.type}' - no kind mapping")
                continue

            if item.status is None or not is_valid_status(item.type, item.status):
                violations.append(f"{rel}: status '{item.status}' invalid for type '{item.type}' (kind={item.kind})")

            if item.scenario and item.scenario not in SCENARIOS:
                violations.append(f"{rel}: unknown scenario '{item.scenario}'")

            expected_prefix = prefix_for_type(item.type)
            if expected_prefix and not item.id.startswith(expected_prefix + "-"):
                violations.append(f"{rel}: id '{item.id}' does not match expected prefix '{expected_prefix}-' for type '{item.type}'")

            for field_name in ("parent", "related", "originated_from", "supersedes", "reverts"):
                target = getattr(item, field_name)
                if target and target not in known_ids:
                    violations.append(f"{rel}: {field_name} '{target}' does not resolve to any known id")

        # tasks.md row validation
        for item in items:
            if item.type != "story":
                continue
            tasks_md = item.path.parent / "tasks.md"
            if not tasks_md.exists():
                continue
            rows = repo.task_rows(item.id)
            seen_ids = set()
            for row in rows:
                if row.id in seen_ids:
                    violations.append(f"{tasks_md.relative_to(repo.root)}: duplicate row id '{row.id}'")
                seen_ids.add(row.id)
                if not is_valid_status("task", row.status):
                    violations.append(f"{tasks_md.relative_to(repo.root)}: row '{row.id}' has invalid status '{row.status}'")

        if violations:
            print(f"VALIDATION FAILED - {len(violations)} violation(s):\n")
            for v in violations:
                print(f"  - {v}")
            sys.exit(1)
        else:
            print(f"OK - {len(items)} file(s) validated, no violations.")
