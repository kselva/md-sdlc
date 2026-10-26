"""
Short layout (0.4.0) - ids, names and paths in one place.

new, promote, item and validate all ask this module, so the naming rule is
written once (CONVENTIONS "Short layout"):

    epic        PAY1                plan/PAY1-checkout/epic.md
    story       PAY1-A or PAY1-2    plan/PAY1-checkout/PAY1-A-card-form/story.md
    row         PAY1-A.3            row in that folder's tasks.md
    experiment  PAY1-E2             plan/PAY1-checkout/PAY1-E2-retry-rate.md
                EXP-<slug>          plan/EXP-<slug>.md (no parent)
    proposal    IDEA-<slug>         plan/ideas/IDEA-<slug>.md
    adhoc       ADHOC-<slug>        plan/ADHOC-<slug>.md
"""
import re
from pathlib import Path

from core.models import WorkItemFile
from core.vocab import short_slug

CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*$")
SHORT_PREFIXES = {"proposal": "IDEA", "adhoc": "ADHOC", "experiment": "EXP"}
IDEAS_DIR = "ideas"


def is_short(repo) -> bool:
    return bool(getattr(repo.project, "is_short", False))


def work_path(repo) -> Path:
    project = repo.project
    return project.work_path if project is not None and hasattr(project, "work_path") else repo.root


def check_code(code: str) -> str | None:
    """Return an error message for a bad epic/story code, None when fine."""
    if not code:
        return "a code is required, e.g. --code PAY1"
    if not CODE_PATTERN.match(code):
        return f"code '{code}' must be capital letters and digits, starting with a letter (e.g. PAY1, A, B2)"
    return None


def _next_number(existing_ids: list[str], prefix: str) -> int:
    pattern = re.compile(re.escape(prefix) + r"(\d+)$")
    numbers = [int(m.group(1)) for m in (pattern.match(i) for i in existing_ids) if m]
    return max(numbers, default=0) + 1


def epic_id(code: str) -> str:
    return code


def story_id(repo, epic: WorkItemFile, code: str | None) -> str:
    if code:
        return f"{epic.id}-{code}"
    siblings = [c.id for c in repo.children_of(epic.id) if c.type == "story"]
    return f"{epic.id}-{_next_number(siblings, epic.id + '-')}"


def experiment_id(repo, parent: WorkItemFile | None, title: str) -> str:
    if parent is None:
        return f"{SHORT_PREFIXES['experiment']}-{short_slug(title)}"
    siblings = [c.id for c in repo.children_of(parent.id) if c.type == "experiment"]
    return f"{parent.id}-E{_next_number(siblings, parent.id + '-E')}"


def plain_id(type_: str, title: str) -> str:
    """proposal / adhoc - prefix + short slug."""
    return f"{SHORT_PREFIXES[type_]}-{short_slug(title)}"


def item_path(repo, type_: str, item_id: str, title: str, parent: WorkItemFile | None) -> Path:
    name = f"{item_id}-{short_slug(title)}" if short_slug(title) else item_id
    if type_ == "epic":
        return work_path(repo) / name / "epic.md"
    if type_ == "story":
        return parent.path.parent / name / "story.md"
    if type_ == "experiment":
        if item_id.startswith(SHORT_PREFIXES["experiment"] + "-") or parent is None:
            return work_path(repo) / f"{item_id}.md"
        return parent.path.parent / f"{name}.md"
    if type_ == "proposal":
        return work_path(repo) / IDEAS_DIR / f"{item_id}.md"
    if type_ == "adhoc":
        return work_path(repo) / f"{item_id}.md"
    raise ValueError(f"type '{type_}' has no short-layout path (tasks are rows: use 'item add')")


def next_row_id(parent_id: str, existing_ids: list[str]) -> str:
    return f"{parent_id}.{_next_number(existing_ids, parent_id + '.')}"


def row_parent_id(row_id: str) -> str | None:
    """PAY1-A.3 -> PAY1-A"""
    head, sep, tail = row_id.rpartition(".")
    return head if sep and tail.isdigit() else None
