"""
Fixed vocabulary for the SDLC tracking model.

These are schema-level constants, not user-editable config - unlike file
*templates* (YAML, per the "config over code" principle), the set of valid
type/status/kind values is fixed so validation has a stable contract.

Source: ai-docs/plan/SDLC_Tracking_System_Design.md, sections 4, 6, 8.
"""

# Lifecycle order - used for column layout in `stats` and any other ordered
# rendering. The set form below is kept for O(1) membership checks.
# parked (0.4.0) - put aside on purpose, not terminal: it can come back.
WORK_ITEM_STATUS_ORDER = ("proposed", "not-started", "in-progress", "in-review", "blocked", "parked", "done", "abandoned")
WORK_ITEM_STATUSES = set(WORK_ITEM_STATUS_ORDER)
ARTIFACT_STATUS_ORDER = ("draft", "approved", "current", "superseded")
ARTIFACT_STATUSES = set(ARTIFACT_STATUS_ORDER)

# Review-row-specific vocabulary (review.md rows, see REVIEW_ROW_COLUMNS) -
# separate from WORK_ITEM_STATUSES because a finding isn't a unit of planned
# work: it has no "not-started" (it exists because it was already found) and
# "changes-requested" sends it back to the author, which has no equivalent
# in the work-item flow.
REVIEW_ROW_STATUS_ORDER = ("open", "changes-requested", "fixed", "wontfix")
REVIEW_ROW_STATUSES = set(REVIEW_ROW_STATUS_ORDER)

# Stability (0.3.0) - a situational field on epic/story that gates how much
# test ceremony is allowed. Separate from status: status is "where is this in
# its lifecycle", stability is "has the customer frozen the behaviour yet".
#   exploring - customer still deciding; smoke test only, skip Task files/review
#   settled   - customer signed off; assertion / golden-file tests allowed
#   locked    - shipped, in user testing; spec and tests frozen
STABILITY_ORDER = ("exploring", "settled", "locked")
STABILITY_VALUES = set(STABILITY_ORDER)

# Filenames matching these globs are treated as assertion/spec tests by
# validate's test gate (a project overrides via .sdlc/config.yml
# test_file_globs). A single file matching smoke_test_glob is exempt - the
# one smoke test an `exploring` Story is allowed.
DEFAULT_TEST_FILE_GLOBS = [
    "*.spec.ts", "*.test.ts", "*.spec.js", "*.test.js",
    "*_test.py", "test_*.py",
]
DEFAULT_SMOKE_TEST_GLOB = "*.smoke.spec.ts"

# type -> kind is a fixed lookup, not an independently-set field. This removes
# an entire class of validation error (kind disagreeing with type) by construction.
TYPE_KIND = {
    "proposal": "work-item",
    "epic": "work-item",
    "story": "work-item",
    "task": "work-item",
    "adhoc": "work-item",
    "experiment": "work-item",
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
    "experiment": "EXP",
}

# Reverse lookup: prefix -> type, used by validate to check filename/id/type agreement
PREFIX_TYPE = {v: k for k, v in ID_PREFIXES.items()}

SCENARIOS = {
    "feature", "enhancement", "bug", "refactor", "spike", "change-request",
    "performance", "docs", "config", "migration", "hotfix", "rollback",
    "deprecation", "compliance", "dependency-upgrade", "research",
    "poc", "quality",
}

TASK_ROW_COLUMNS = ["id", "status", "scenario", "owner", "updated", "summary"]
# Short layout (0.4.0) row columns. Rows are read by header name, so either
# column set (or a hand-reordered table) parses the same way.
SHORT_ROW_COLUMNS = ["id", "status", "waits", "verdict", "updated", "summary"]

# Experiment verdict (0.4.0) - on experiment files and experiment rows.
VERDICT_ORDER = ("open", "yes", "no", "partly")
VERDICTS = set(VERDICT_ORDER)

# id_style values in .sdlc/config.yml (0.4.0).
ID_STYLE_CLASSIC = "classic"
ID_STYLE_SHORT = "short"

# Short layout naming limits: a folder/file name is the id plus up to
# SLUG_WORDS words, and should stay under NAME_WARN_LENGTH characters.
SLUG_WORDS = 3
NAME_WARN_LENGTH = 40

# Files with a fixed role inside an item folder - never tracked items themselves.
ROW_TABLE_FILE = "tasks.md"
LOG_FILE = "log.md"
FOLDER_ITEM_FILES = ("epic.md", "story.md")
REVIEW_ROW_COLUMNS = ["id", "severity", "status", "summary", "reported_by", "updated"]
REVIEW_SEVERITY_ORDER = ("critical", "high", "medium", "low")
REVIEW_SEVERITIES = set(REVIEW_SEVERITY_ORDER)


def slugify(title: str) -> str:
    import re
    slug = title.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def short_slug(title: str, words: int = SLUG_WORDS) -> str:
    """First few words of slugify(title) - keeps short-layout names short."""
    return "-".join(slugify(title).split("-")[:words])


def is_valid_verdict(value: str) -> bool:
    return value in VERDICTS


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


def is_valid_stability(value: str) -> bool:
    return value in STABILITY_VALUES


def prefix_for_type(type_: str) -> str | None:
    return ID_PREFIXES.get(type_)


def type_for_prefix(prefix: str) -> str | None:
    return PREFIX_TYPE.get(prefix)


TERMINAL_STATUSES = {"done", "abandoned", "superseded"}


def is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES
