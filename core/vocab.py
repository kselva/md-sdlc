"""
Fixed vocabulary for the SDLC tracking model.

These are schema-level constants, not user-editable config - unlike file
*templates* (YAML, per the "config over code" principle), the set of valid
type/status/kind values is fixed so validation has a stable contract.

Source: ai-docs/plan/SDLC_Tracking_System_Design.md, sections 4, 6, 8.
"""

WORK_ITEM_STATUSES = {"proposed", "not-started", "in-progress", "in-review", "blocked", "done", "abandoned"}
ARTIFACT_STATUSES = {"draft", "approved", "current", "superseded"}

# Review-row-specific vocabulary (review.md rows, see REVIEW_ROW_COLUMNS) -
# separate from WORK_ITEM_STATUSES because a finding isn't a unit of planned
# work: it has no "not-started" (it exists because it was already found) and
# "changes-requested" sends it back to the author, which has no equivalent
# in the work-item flow.
REVIEW_ROW_STATUSES = {"open", "changes-requested", "fixed", "wontfix"}

# type -> kind is a fixed lookup, not an independently-set field. This removes
# an entire class of validation error (kind disagreeing with type) by construction.
TYPE_KIND = {
    "proposal": "work-item",
    "epic": "work-item",
    "story": "work-item",
    "task": "work-item",
    "adhoc": "work-item",
    "analysis": "artifact",
    "design-lld": "artifact",
    "design-hld": "artifact",
    "design-tech-notes": "artifact",
    "report": "artifact",
    "reference": "artifact",
    "guide": "artifact",
    "query": "artifact",
    "schema": "artifact",
}

ID_PREFIXES = {
    "proposal": "PROPOSAL",
    "epic": "EPIC",
    "story": "STORY",
    "task": "TASK",
    "adhoc": "ADHOC",
}

# Reverse lookup: prefix -> type, used by validate to check filename/id/type agreement
PREFIX_TYPE = {v: k for k, v in ID_PREFIXES.items()}

SCENARIOS = {
    "feature", "enhancement", "bug", "refactor", "spike", "change-request",
    "performance", "docs", "config", "migration", "hotfix", "rollback",
    "deprecation", "compliance", "dependency-upgrade", "research",
}

TASK_ROW_COLUMNS = ["id", "status", "scenario", "owner", "updated", "summary"]
REVIEW_ROW_COLUMNS = ["id", "severity", "status", "summary", "reported_by", "updated"]
REVIEW_SEVERITIES = {"critical", "high", "medium", "low"}


def slugify(title: str) -> str:
    import re
    slug = title.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def kind_for_type(type_: str) -> str | None:
    return TYPE_KIND.get(type_)


def statuses_for_kind(kind: str) -> set[str]:
    if kind == "work-item":
        return WORK_ITEM_STATUSES
    if kind == "artifact":
        return ARTIFACT_STATUSES
    return set()


def is_valid_status(type_: str, status: str) -> bool:
    kind = kind_for_type(type_)
    if kind is None:
        return False
    return status in statuses_for_kind(kind)


def is_valid_review_status(status: str) -> bool:
    return status in REVIEW_ROW_STATUSES


def prefix_for_type(type_: str) -> str | None:
    return ID_PREFIXES.get(type_)


def type_for_prefix(prefix: str) -> str | None:
    return PREFIX_TYPE.get(prefix)


TERMINAL_STATUSES = {"done", "abandoned", "superseded"}


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES
