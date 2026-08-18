"""
Data model for work-items and artifacts read from the ai-docs tree.

WorkItemFile represents any file with a frontmatter header (Epic/Story/Task/
Adhoc/Proposal/artifact). TaskRow represents a single row inside a Story's
tasks.md table - kept separate because a promoted row becomes a WorkItemFile
and the promote plugin needs to convert cleanly between the two.
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
    extra: dict = field(default_factory=dict)
    body: str = ""


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
