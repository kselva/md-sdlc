"""
Data model for work-items and artifacts read from the ai-docs tree.

WorkItemFile represents any file with a frontmatter header (Epic/Story/Task/
Adhoc/Proposal/artifact). TaskRow represents a single row inside a Story's
tasks.md table - kept separate because a promoted row becomes a WorkItemFile
and the promote plugin needs to convert cleanly between the two. ReviewRow
is the same row-table pattern applied to review.md - a reviewer's findings
on a Story, tracked separately from planned work (tasks.md) since a finding
isn't work that was planned, it's feedback on work already done.
"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WorkItemFile:
    id: str
    type: str
    kind: str
    status: str
    path: Path
    parent: str | None = None
    owner: str | None = None
    updated: str | None = None
    scenario: str | None = None
    project: str | None = None
    mvp: bool | None = None
    related: str | None = None
    originated_from: str | None = None
    supersedes: str | None = None
    reverts: str | None = None
    promoted: str | None = None
    # 0.3.0 situational fields (epic/story). stability gates test ceremony
    # (see core.vocab.STABILITY_VALUES); touches is an advisory list of
    # repo-relative path globs the Story expects to edit, used by validate's
    # overlap warning and by `handover` - never checked against the filesystem.
    stability: str | None = None
    touches: list[str] = field(default_factory=list)
    # 0.4.0 situational fields. title carries the full name now that short
    # layout keeps file names short; next / waits_on / deployed feed the
    # status view; question / result / verdict are for experiments.
    title: str | None = None
    next: str | None = None
    waits_on: str | None = None
    deployed: str | None = None
    question: str | None = None
    result: str | None = None
    verdict: str | None = None
    adopted: str | None = None
    extra: dict = field(default_factory=dict)
    body: str = ""

    @property
    def display_title(self) -> str:
        """Header title, else the body's first '# ' heading, else the id."""
        if self.title:
            return str(self.title)
        for line in self.body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return self.id

    @property
    def is_folder_item(self) -> bool:
        """True for epic.md / story.md - the item owns its whole folder."""
        return self.path.name in ("epic.md", "story.md")


@dataclass
class TaskRow:
    id: str
    status: str
    scenario: str | None
    owner: str | None
    updated: str | None
    summary: str
    story_id: str
    row_index: int
    # 0.4.0 short-layout columns (absent in classic tables)
    waits: str | None = None
    verdict: str | None = None


@dataclass
class ReviewRow:
    id: str
    severity: str | None
    status: str
    summary: str
    reported_by: str | None
    updated: str | None
    story_id: str
    row_index: int
