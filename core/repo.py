"""
AiDocsRepo - the only class that touches the filesystem.

Every plugin depends on this, never on pathlib/open() directly (design doc
SDLC_Tracking_System_Design.md section 10.2, "one client, many callers").
"""
import logging
import re
from pathlib import Path

from core import frontmatter as fmparse
from core.models import ReviewRow, TaskRow, WorkItemFile
from core.vocab import REVIEW_ROW_COLUMNS, TASK_ROW_COLUMNS, kind_for_type

logger = logging.getLogger(__name__)

_KNOWN_FIELDS = {
    "id", "type", "kind", "status", "parent", "owner", "updated", "scenario",
    "project", "mvp", "related", "originated_from", "supersedes", "reverts", "promoted",
}


class AiDocsRepo:
    def __init__(self, root: Path, project=None):
        self.root = Path(root)
        self.project = project

    _ROW_TABLE_FILENAMES = {"tasks.md", "review.md"}

    def all_files(self) -> list[WorkItemFile]:
        """Walk the tree, parse frontmatter from every .md file that has any."""
        items = []
        for path in sorted(self.root.rglob("*.md")):
            if path.name in self._ROW_TABLE_FILENAMES:
                continue  # rows, not a single record - see task_rows()/review_rows()
            if ".sdlc" in path.parts:
                continue  # marker folder, never tracked content
            item = self._parse_file(path)
            if item is not None:
                items.append(item)
        return items

    def _parse_file(self, path: Path) -> WorkItemFile | None:
        try:
            meta, body = fmparse.parse(path)
        except Exception as exc:
            logger.warning("Failed to parse frontmatter in %s: %s", path, exc)
            return None
        if not meta or "id" not in meta:
            return None  # not a tracked file (e.g. a plain README)

        extra = {k: v for k, v in meta.items() if k not in _KNOWN_FIELDS}
        return WorkItemFile(
            id=meta.get("id"),
            type=meta.get("type"),
            kind=meta.get("kind") or kind_for_type(meta.get("type", "")),
            status=meta.get("status"),
            path=path,
            parent=meta.get("parent"),
            owner=meta.get("owner"),
            updated=meta.get("updated"),
            scenario=meta.get("scenario"),
            project=meta.get("project"),
            mvp=meta.get("mvp"),
            related=meta.get("related"),
            originated_from=meta.get("originated_from"),
            supersedes=meta.get("supersedes"),
            reverts=meta.get("reverts"),
            promoted=meta.get("promoted"),
            extra=extra,
            body=body,
        )

    def find(self, item_id: str) -> WorkItemFile | None:
        for item in self.all_files():
            if item.id == item_id:
                return item
        return None

    def children_of(self, item_id: str) -> list[WorkItemFile]:
        return [item for item in self.all_files() if item.parent == item_id]

    def task_rows(self, story_id: str) -> list[TaskRow]:
        """Read the tasks.md table for a given Story, if it exists."""
        rows = self._read_row_table(story_id, "tasks.md", TASK_ROW_COLUMNS)
        return [
            TaskRow(
                id=r["id"], status=r["status"], scenario=r.get("scenario") or None,
                owner=r.get("owner") or None, updated=r.get("updated") or None,
                summary=r.get("summary", ""), story_id=story_id, row_index=idx,
            )
            for idx, r in enumerate(rows)
        ]

    def review_rows(self, story_id: str) -> list[ReviewRow]:
        """Read the review.md table for a given Story, if it exists."""
        rows = self._read_row_table(story_id, "review.md", REVIEW_ROW_COLUMNS)
        return [
            ReviewRow(
                id=r["id"], severity=r.get("severity") or None, status=r["status"],
                summary=r.get("summary", ""), reported_by=r.get("reported_by") or None,
                updated=r.get("updated") or None, story_id=story_id, row_index=idx,
            )
            for idx, r in enumerate(rows)
        ]

    def _read_row_table(self, story_id: str, filename: str, columns: list[str]) -> list[dict]:
        story = self.find(story_id)
        if story is None:
            return []
        table_path = story.path.parent / filename
        if not table_path.exists():
            return []
        return self._parse_markdown_table(table_path, columns)

    @staticmethod
    def _parse_markdown_table(path: Path, columns: list[str]) -> list[dict]:
        rows = []
        text = path.read_text(encoding="utf-8")
        lines = [l for l in text.splitlines() if l.strip().startswith("|")]
        if len(lines) < 2:
            return rows
        # skip header + separator line
        for line in lines[2:]:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < len(columns):
                continue
            rows.append(dict(zip(columns, cells)))
        return rows

    def next_sequence(self, parent_id: str, type_: str) -> int:
        """Compute the next NN for TASK-<nn>/STORY-<nn> under a parent."""
        siblings = self.children_of(parent_id)
        max_n = 0
        for s in siblings:
            if s.type != type_:
                continue
            match = re.search(r"-(\d+)-", s.id + "-")
            if match:
                max_n = max(max_n, int(match.group(1)))
        return max_n + 1

    def next_review_sequence(self, story_id: str) -> int:
        """Compute the next NN for RVW-<nn> rows in a Story's review.md."""
        rows = self.review_rows(story_id)
        max_n = 0
        for r in rows:
            match = re.search(r"(\d+)$", r.id)
            if match:
                max_n = max(max_n, int(match.group(1)))
        return max_n + 1
