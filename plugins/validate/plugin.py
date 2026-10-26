"""
validate - walk the tree, check schema, vocabulary, and referential integrity.

Design doc reference: SDLC_Tracking_System_Design.md section 10.4 (#1),
Implementation plan section 5.1.

0.3.0 adds a stability test gate (see CONVENTIONS.md and
PROPOSAL-0.3.0-...). Findings are now split into ERRORS (exit 1) and
WARNINGS (printed, exit 0) - sequencing and ceremony calls are advisory,
schema/vocab/link breakage stays fatal.

0.4.0: duplicate ids and unknown verdicts are errors in both layouts. In
short layout (id_style: short) the fixed rules of CONVENTIONS "Short
layout" apply instead of the classic id-prefix check - see _check_short.
"""
import argparse
import sys
from pathlib import Path

from core import layout
from core.repo import AiDocsRepo
from core.vocab import (
    FOLDER_ITEM_FILES,
    LOG_FILE,
    NAME_WARN_LENGTH,
    ROW_TABLE_FILE,
    SCENARIOS,
    STABILITY_VALUES,
    is_valid_review_status,
    is_valid_stability,
    is_valid_status,
    is_valid_verdict,
    prefix_for_type,
)
from plugins.base_plugin import BaseCommand

_ACTIVE_STATUSES = ("in-progress", "in-review")
_OPEN_STATUSES = ("in-progress", "in-review", "blocked")
# .md files allowed loose under work_dir in short layout
_ALLOWED_LOOSE = {ROW_TABLE_FILE, LOG_FILE, "review.md", "backlog.md", "README.md"}


class Command(BaseCommand):
    name = "validate"
    description = "Validate frontmatter schema, vocabulary, and links across the tree"

    def register_args(self, parser: argparse.ArgumentParser) -> None:
        pass  # no options - always validates the whole tree

    def run(self, repo: AiDocsRepo, args: argparse.Namespace) -> None:
        errors, warnings = self.collect(repo)

        for w in warnings:
            print(f"  WARN  {w}")
        if warnings:
            print()

        if errors:
            print(f"VALIDATION FAILED - {len(errors)} error(s), {len(warnings)} warning(s):\n")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)

        n = len(repo.all_files())
        if warnings:
            print(f"OK - {n} file(s) validated, 0 errors, {len(warnings)} warning(s).")
        else:
            print(f"OK - {n} file(s) validated, no violations.")

    # -- collection -------------------------------------------------------

    def collect(self, repo: AiDocsRepo) -> tuple[list[str], list[str]]:
        """Return (errors, warnings). Split out from run() so `handover` can
        reuse the same gate without driving process exit."""
        errors: list[str] = []
        warnings: list[str] = []

        items = repo.all_files()
        known_ids = {item.id for item in items}
        short = layout.is_short(repo)

        for dup_id, dups in sorted(repo.duplicate_ids().items()):
            paths = ", ".join(str(d.path.relative_to(repo.root)) for d in dups)
            errors.append(f"duplicate id '{dup_id}' in {paths}")

        for item in items:
            rel = item.path.relative_to(repo.root)

            if item.kind is None:
                errors.append(f"{rel}: unknown type '{item.type}' - no kind mapping")
                continue

            if item.status is None or not is_valid_status(item.type, item.status):
                errors.append(
                    f"{rel}: status '{item.status}' invalid for type '{item.type}' (kind={item.kind})"
                )

            if item.scenario and item.scenario not in SCENARIOS:
                errors.append(f"{rel}: unknown scenario '{item.scenario}'")

            if item.stability is not None and not is_valid_stability(item.stability):
                errors.append(
                    f"{rel}: stability '{item.stability}' not one of "
                    f"{sorted(STABILITY_VALUES)}"
                )

            if item.verdict is not None and not is_valid_verdict(item.verdict):
                errors.append(f"{rel}: verdict '{item.verdict}' not one of open, yes, no, partly")

            expected_prefix = prefix_for_type(item.type)
            if not short and expected_prefix and not item.id.startswith(expected_prefix + "-"):
                errors.append(
                    f"{rel}: id '{item.id}' does not match expected prefix "
                    f"'{expected_prefix}-' for type '{item.type}'"
                )

            for field_name in ("parent", "related", "originated_from", "supersedes", "reverts"):
                target = getattr(item, field_name)
                if target and target not in known_ids:
                    errors.append(
                        f"{rel}: {field_name} '{target}' does not resolve to any known id"
                    )

        self._check_rows(repo, items, errors)
        if short:
            self._check_short(repo, items, errors, warnings)
        self._check_stability_gate(repo, items, errors, warnings)
        self._check_touches_overlap(items, warnings)

        return errors, warnings

    # -- row tables (unchanged behaviour) --------------------------------

    def _check_rows(self, repo: AiDocsRepo, items: list, errors: list[str]) -> None:
        for item in items:
            if item.type != "story" and not (item.type == "epic" and layout.is_short(repo)):
                continue

            tasks_md = item.path.parent / "tasks.md"
            if tasks_md.exists():
                seen: set[str] = set()
                for row in repo.task_rows(item.id):
                    if row.id in seen:
                        errors.append(
                            f"{tasks_md.relative_to(repo.root)}: duplicate row id '{row.id}'"
                        )
                    seen.add(row.id)
                    if not is_valid_status("task", row.status):
                        errors.append(
                            f"{tasks_md.relative_to(repo.root)}: row '{row.id}' has "
                            f"invalid status '{row.status}'"
                        )
                    if row.verdict is not None and not is_valid_verdict(row.verdict):
                        errors.append(
                            f"{tasks_md.relative_to(repo.root)}: row '{row.id}' has "
                            f"invalid verdict '{row.verdict}'"
                        )

            review_md = item.path.parent / "review.md"
            if review_md.exists():
                rows = repo.review_rows(item.id)
                seen = set()
                for row in rows:
                    if row.id in seen:
                        errors.append(
                            f"{review_md.relative_to(repo.root)}: duplicate finding id '{row.id}'"
                        )
                    seen.add(row.id)
                    if not is_valid_review_status(row.status):
                        errors.append(
                            f"{review_md.relative_to(repo.root)}: finding '{row.id}' has "
                            f"invalid status '{row.status}'"
                        )

                if item.status == "done":
                    for row in [r for r in rows if r.status in ("open", "changes-requested")]:
                        errors.append(
                            f"{item.path.relative_to(repo.root)}: status is 'done' but "
                            f"{review_md.relative_to(repo.root)} has unresolved finding "
                            f"'{row.id}' (status={row.status})"
                        )

    # -- 0.4.0 short layout rules ----------------------------------------

    def _check_short(self, repo: AiDocsRepo, items: list, errors: list[str], warnings: list[str]) -> None:
        by_id = {i.id: i for i in items}
        work = layout.work_path(repo).resolve()

        for item in items:
            if item.kind != "work-item" or repo.is_archived(item):
                continue
            rel = item.path.relative_to(repo.root)
            name = item.path.parent.name if item.is_folder_item else item.path.stem

            if item.type == "story" and item.parent in by_id and not item.id.startswith(item.parent + "-"):
                errors.append(f"{rel}: story id '{item.id}' must start with its epic id '{item.parent}-'")
            if not item.adopted and _is_under(item.path, work) and not (name == item.id or name.startswith(item.id + "-")):
                errors.append(f"{rel}: name '{name}' must start with its id '{item.id}' (or adopt the file)")
            if len(name) > NAME_WARN_LENGTH:
                warnings.append(f"{rel}: name '{name}' is {len(name)} characters - keep it under {NAME_WARN_LENGTH}")
            if item.type in ("epic", "story") and item.status in _OPEN_STATUSES and not item.next:
                warnings.append(f"{rel}: {item.status} {item.type} has no 'next:' line")

        if work == repo.root.resolve():
            return  # no work_dir - the loose-file rule needs a dedicated folder
        tracked = {i.path.resolve() for i in items}
        item_folders = {i.path.parent.resolve() for i in items if i.path.name in FOLDER_ITEM_FILES}
        for path in sorted(work.rglob("*.md")):
            path = path.resolve()
            if path in tracked or path.name in _ALLOWED_LOOSE:
                continue
            if any(parent in item_folders for parent in path.parents):
                continue  # attached to an epic/story
            errors.append(
                f"{path.relative_to(repo.root.resolve())}: loose file in {repo.project.work_dir}/ - "
                f"adopt it (adopt FILE --type ... --id ...) or move it"
            )

    # -- 0.3.0 stability test gate --------------------------------------

    def _check_stability_gate(
        self, repo: AiDocsRepo, items: list, errors: list[str], warnings: list[str]
    ) -> None:
        project = getattr(repo, "project", None)
        code_root = getattr(project, "code_root", None) or repo.root.parent
        test_globs = getattr(project, "test_file_globs", None) or []
        smoke_glob = getattr(project, "smoke_test_glob", None)

        for item in items:
            if item.type not in ("epic", "story") or item.stability != "exploring":
                continue
            rel = item.path.relative_to(repo.root)

            # Rule 1 (ERROR) - assertion/spec test file under this Story's
            # touches: paths. Directory listing only; no file is read or run.
            if item.type == "story" and item.touches:
                hits = self._spec_files_under(code_root, item.touches, test_globs, smoke_glob)
                for hit in hits:
                    errors.append(
                        f"{rel}: stability is 'exploring' but a spec/assertion test "
                        f"file exists under touches: -> {hit} "
                        f"(smoke test only until 'settled')"
                    )

            # Rule 2 (WARNING) - a promoted TASK-xx.md file this early.
            promoted_tasks = [
                c for c in repo.children_of(item.id)
                if c.type == "task" and c.path.name.lower() != "tasks.md"
            ]
            for t in promoted_tasks:
                warnings.append(
                    f"{rel}: stability 'exploring' but child Task '{t.id}' is a "
                    f"promoted file - keep tasks as rows until behaviour settles"
                )

            # Rule 3 (WARNING) - about to ship unfrozen work.
            if item.status == "done":
                warnings.append(
                    f"{rel}: status '{item.status}' while stability is 'exploring' - "
                    f"freezing behaviour (settled/locked) should come first"
                )

    @staticmethod
    def _spec_files_under(
        code_root: Path,
        touches: list[str],
        test_globs: list[str],
        smoke_glob: str | None,
    ) -> list[str]:
        """List files under any touches: path whose name matches a test glob
        (excluding a single smoke-test glob). Reads directory entries only."""
        found: list[str] = []
        code_root = Path(code_root)
        for raw in touches:
            spec = raw.strip().strip("/")
            if not spec:
                continue
            base = code_root / spec
            candidates: list[Path] = []
            if base.is_dir():
                candidates = [p for p in base.rglob("*") if p.is_file()]
            elif base.exists():
                candidates = [base]
            else:
                # touches: may itself contain a glob (e.g. .../*.ts)
                try:
                    candidates = [p for p in code_root.glob(spec) if p.is_file()]
                except (ValueError, OSError):
                    candidates = []
            for path in candidates:
                name = path.name
                if smoke_glob and _fnmatch(name, smoke_glob):
                    continue
                if any(_fnmatch(name, g) for g in test_globs):
                    try:
                        found.append(str(path.relative_to(code_root)))
                    except ValueError:
                        found.append(str(path))
        return sorted(set(found))

    # -- 0.3.0 touches: overlap warning -------------------------------

    def _check_touches_overlap(self, items: list, warnings: list[str]) -> None:
        active = [
            i for i in items
            if i.type == "story" and i.status in _ACTIVE_STATUSES and i.touches
        ]
        for a_idx in range(len(active)):
            for b_idx in range(a_idx + 1, len(active)):
                a, b = active[a_idx], active[b_idx]
                shared = _overlapping_prefixes(a.touches, b.touches)
                for path in shared:
                    warnings.append(
                        f"touches: overlap - '{a.id}' and '{b.id}' are both active "
                        f"and both touch '{path}' - sequence them or split the work"
                    )


def _fnmatch(name: str, pattern: str) -> bool:
    from fnmatch import fnmatch
    return fnmatch(name, pattern)


def _overlapping_prefixes(a: list[str], b: list[str]) -> list[str]:
    """Return the touches: entries where one is a path-prefix of the other."""
    out: list[str] = []
    norm_a = [x.strip().strip("/") for x in a if x.strip()]
    norm_b = [x.strip().strip("/") for x in b if x.strip()]
    for pa in norm_a:
        for pb in norm_b:
            if pa == pb or _is_prefix(pa, pb) or _is_prefix(pb, pa):
                out.append(pa if len(pa) <= len(pb) else pb)
    return sorted(set(out))


def _is_prefix(short: str, long: str) -> bool:
    if not short or not long or len(short) >= len(long):
        return False
    return long.startswith(short.rstrip("/") + "/")


def _is_under(path: Path, folder: Path) -> bool:
    try:
        path.resolve().relative_to(folder)
        return True
    except ValueError:
        return False
