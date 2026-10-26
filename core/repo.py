"""
AiDocsRepo - the only class that touches the filesystem.

Every plugin depends on this, never on pathlib/open() directly (design doc
SDLC_Tracking_System_Design.md section 10.2, "one client, many callers").

0.4.0: the parsed tree is cached per instance (each lookup used to re-walk
the whole tree) and every write goes through a helper here that drops the
cache. Row tables are read by header name, so reordered columns and the
short-layout column set parse the same way.
"""
import datetime
import logging
import re
from pathlib import Path

from core import frontmatter as fmparse
from core.models import ReviewRow, TaskRow, WorkItemFile
from core.vocab import (
    LOG_FILE,
    REVIEW_ROW_COLUMNS,
    ROW_TABLE_FILE,
    SHORT_ROW_COLUMNS,
    TASK_ROW_COLUMNS,
    kind_for_type,
)

logger = logging.getLogger(__name__)

_KNOWN_FIELDS = {
    "id", "type", "kind", "status", "parent", "owner", "updated", "scenario",
    "project", "mvp", "related", "originated_from", "supersedes", "reverts", "promoted",
    "stability", "touches",
    "title", "next", "waits_on", "deployed", "question", "result", "verdict", "adopted",
}

# Every column name the tool knows - a header made only of these is read by name.
_KNOWN_COLUMNS = set(TASK_ROW_COLUMNS) | set(SHORT_ROW_COLUMNS) | set(REVIEW_ROW_COLUMNS)

# Unescaped pipe - a cell may hold a literal '|' written as '\|'.
_CELL_SPLIT = re.compile(r"(?<!\\)\|")


def _as_str_list(value) -> list[str]:
    """Coerce a frontmatter value to a list of strings.

    touches: may be authored as a YAML list or, for a single path, a bare
    string - accept both so a one-path Story isn't forced into list syntax.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _as_text(value) -> str | None:
    """Header values may parse as dates or numbers - the model holds text."""
    if value is None:
        return None
    return str(value)


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return None if value in ("", "-") else value


def _escape_cell(value) -> str:
    text = "" if value is None else str(value)
    return text.replace("\n", " ").replace("|", "\\|").strip()


def today() -> str:
    return datetime.date.today().isoformat()


def today_date() -> datetime.date:
    """For headers - a date object dumps unquoted, like hand-written headers."""
    return datetime.date.today()


class AiDocsRepo:
    def __init__(self, root: Path, project=None):
        self.root = Path(root)
        self.project = project
        self._items: list[WorkItemFile] | None = None
        self._by_id: dict[str, WorkItemFile] = {}

    _ROW_TABLE_FILENAMES = {"tasks.md", "review.md", LOG_FILE}

    # -- reading -------------------------------------------------------------

    def all_files(self) -> list[WorkItemFile]:
        """Walk the tree once, parse frontmatter from every .md file that has any."""
        if self._items is None:
            items = []
            for path in sorted(self.root.rglob("*.md")):
                if path.name in self._ROW_TABLE_FILENAMES:
                    continue  # rows / log lines, not a single record
                if ".sdlc" in path.parts:
                    continue  # marker folder, never tracked content
                item = self._parse_file(path)
                if item is not None:
                    items.append(item)
            self._items = items
            self._by_id = {}
            for item in items:
                self._by_id.setdefault(item.id, item)  # first wins; validate reports duplicates
        return self._items

    def invalidate(self) -> None:
        """Drop the cached tree - every write helper calls this."""
        self._items = None
        self._by_id = {}

    def duplicate_ids(self) -> dict[str, list[WorkItemFile]]:
        seen: dict[str, list[WorkItemFile]] = {}
        for item in self.all_files():
            seen.setdefault(item.id, []).append(item)
        return {k: v for k, v in seen.items() if len(v) > 1}

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
            id=str(meta.get("id")),
            type=meta.get("type"),
            kind=meta.get("kind") or kind_for_type(meta.get("type", "")),
            status=meta.get("status"),
            path=path,
            parent=meta.get("parent"),
            owner=meta.get("owner"),
            updated=_as_text(meta.get("updated")),
            scenario=meta.get("scenario"),
            project=meta.get("project"),
            mvp=meta.get("mvp"),
            related=meta.get("related"),
            originated_from=meta.get("originated_from"),
            supersedes=meta.get("supersedes"),
            reverts=meta.get("reverts"),
            promoted=meta.get("promoted"),
            stability=meta.get("stability"),
            touches=_as_str_list(meta.get("touches")),
            title=_as_text(meta.get("title")),
            next=_as_text(meta.get("next")),
            waits_on=_as_text(meta.get("waits_on")),
            deployed=_as_text(meta.get("deployed")),
            question=_as_text(meta.get("question")),
            result=_as_text(meta.get("result")),
            verdict=_as_text(meta.get("verdict")),
            adopted=_as_text(meta.get("adopted")),
            extra=extra,
            body=body,
        )

    def find(self, item_id: str) -> WorkItemFile | None:
        self.all_files()
        return self._by_id.get(item_id)

    def children_of(self, item_id: str) -> list[WorkItemFile]:
        return [item for item in self.all_files() if item.parent == item_id]

    def is_archived(self, item: WorkItemFile) -> bool:
        """True for items under hist/ - kept for links, left out of status."""
        try:
            return item.path.relative_to(self.root).parts[0] == "hist"
        except (ValueError, IndexError):
            return False

    def task_rows(self, story_id: str) -> list[TaskRow]:
        """Read the tasks.md table for a Story (or, in short layout, an Epic)."""
        rows = self._read_row_table(story_id, ROW_TABLE_FILE, TASK_ROW_COLUMNS)
        return [
            TaskRow(
                id=r["id"], status=r.get("status", ""), scenario=r.get("scenario") or None,
                owner=r.get("owner") or None, updated=r.get("updated") or None,
                summary=r.get("summary", ""), story_id=story_id, row_index=idx,
                waits=_blank_to_none(r.get("waits")), verdict=_blank_to_none(r.get("verdict")),
            )
            for idx, r in enumerate(rows)
        ]

    def review_rows(self, story_id: str) -> list[ReviewRow]:
        """Read the review.md table for a given Story, if it exists."""
        rows = self._read_row_table(story_id, "review.md", REVIEW_ROW_COLUMNS)
        return [
            ReviewRow(
                id=r["id"], severity=r.get("severity") or None, status=r.get("status", ""),
                summary=r.get("summary", ""), reported_by=r.get("reported_by") or None,
                updated=r.get("updated") or None, story_id=story_id, row_index=idx,
            )
            for idx, r in enumerate(rows)
        ]

    def _read_row_table(self, item_id: str, filename: str, columns: list[str]) -> list[dict]:
        item = self.find(item_id)
        if item is None or not item.is_folder_item:
            return []  # a single-file item has no folder of its own to hold rows
        table_path = item.path.parent / filename
        if not table_path.exists():
            return []
        return self._parse_markdown_table(table_path, columns)

    @staticmethod
    def _split_cells(line: str) -> list[str]:
        text = line.strip()
        if text.startswith("|"):
            text = text[1:]
        if text.endswith("|") and not text.endswith("\\|"):
            text = text[:-1]
        return [c.strip().replace("\\|", "|") for c in _CELL_SPLIT.split(text)]

    @classmethod
    def _parse_markdown_table(cls, path: Path, columns: list[str]) -> list[dict]:
        """Read the first table in the file. A header made of known column
        names is read by name; any other header falls back to position."""
        rows = []
        text = path.read_text(encoding="utf-8")
        lines = [l for l in text.splitlines() if l.strip().startswith("|")]
        if len(lines) < 2:
            return rows
        header = [h.lower().replace(" ", "_") for h in cls._split_cells(lines[0])]
        by_name = "id" in header and set(header) <= _KNOWN_COLUMNS
        names = header if by_name else columns
        for line in lines[2:]:
            cells = cls._split_cells(line)
            if len(cells) < len(names):
                if not by_name:
                    continue  # 0.3.0 behaviour for unknown headers
                cells += [""] * (len(names) - len(cells))
            row = dict(zip(names, cells))
            if row.get("id"):
                rows.append(row)
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

    def log_lines(self, item: WorkItemFile, limit: int = 5) -> list[str]:
        if not item.is_folder_item:
            return []
        path = item.path.parent / LOG_FILE
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        return [l[2:] for l in lines if l.startswith("- ")][:limit]

    def attached_files(self, item: WorkItemFile) -> list[str]:
        """Files in an item's folder that are neither tracked items nor its fixed files."""
        if not item.is_folder_item:
            return []
        tracked = {i.path for i in self.all_files()}
        fixed = {item.path.name, ROW_TABLE_FILE, LOG_FILE, "review.md"}
        return [
            p.name for p in sorted(item.path.parent.iterdir())
            if p.is_file() and p.name not in fixed and p not in tracked
        ]

    # -- writing (0.4.0) -----------------------------------------------------

    def write_item(self, path: Path, meta: dict, body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fmparse.write(path, meta, body)
        self.invalidate()

    def update_header(self, item: WorkItemFile, changes: dict, touch: bool = True) -> None:
        """Change header fields in place. Other fields, key order and body are
        kept; a None value removes the field; touch sets updated to today."""
        meta, body = fmparse.parse(item.path)
        for key, value in changes.items():
            if value is None:
                meta.pop(key, None)
            else:
                meta[key] = value
        if touch:
            meta["updated"] = today_date()
        fmparse.write(item.path, meta, body)
        self.invalidate()

    def add_header(self, path: Path, meta: dict) -> None:
        """Put a header on an existing untracked file; the body is not touched."""
        old_meta, body = fmparse.parse(path)
        if old_meta.get("id"):
            raise ValueError(f"{path.name} already has a header (id '{old_meta['id']}')")
        merged = dict(meta)
        merged.update({k: v for k, v in old_meta.items() if k not in merged})
        fmparse.write(path, merged, body)
        self.invalidate()

    def raw_rows(self, item: WorkItemFile) -> tuple[list[str], list[dict]]:
        """An item's tasks.md as (columns, rows) keeping the file's own
        columns, so a write-back never drops a column. Short columns when
        the file is missing or its header is not known."""
        path = item.path.parent / ROW_TABLE_FILE
        if not path.exists():
            return list(SHORT_ROW_COLUMNS), []
        lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip().startswith("|")]
        header = [h.lower().replace(" ", "_") for h in self._split_cells(lines[0])] if lines else []
        if not ("id" in header and set(header) <= _KNOWN_COLUMNS):
            header = list(TASK_ROW_COLUMNS) if lines else list(SHORT_ROW_COLUMNS)
        return header, self._parse_markdown_table(path, header)

    def write_rows(self, item: WorkItemFile, rows: list[dict], columns: list[str] = SHORT_ROW_COLUMNS) -> Path:
        """Rewrite the first table in the item's tasks.md, keeping the text
        around it. Creates the file when missing."""
        path = item.path.parent / ROW_TABLE_FILE
        table = ["| " + " | ".join(columns) + " |", "|" + "|".join("----" for _ in columns) + "|"]
        table += ["| " + " | ".join(_escape_cell(r.get(c)) for c in columns) + " |" for r in rows]

        if path.exists():
            lines = path.read_text(encoding="utf-8").splitlines()
        else:
            lines = [f"# Open items - {item.id}", ""]
        start = next((i for i, l in enumerate(lines) if l.strip().startswith("|")), None)
        if start is None:
            out = lines + table
        else:
            end = start
            while end < len(lines) and lines[end].strip().startswith("|"):
                end += 1
            out = lines[:start] + table + lines[end:]
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
        self.invalidate()
        return path

    def init_item_folder(self, item_id: str, folder: Path) -> None:
        """Empty tasks.md and log.md for a new short-layout epic/story."""
        table = ["| " + " | ".join(SHORT_ROW_COLUMNS) + " |", "|" + "|".join("----" for _ in SHORT_ROW_COLUMNS) + "|"]
        (folder / ROW_TABLE_FILE).write_text("\n".join([f"# Open items - {item_id}", ""] + table) + "\n", encoding="utf-8")
        (folder / LOG_FILE).write_text(f"# Log - {item_id}\n\n", encoding="utf-8")

    def append_log(self, item: WorkItemFile, text: str) -> Path:
        """Add a dated line on top of the item's log.md (newest first)."""
        path = item.path.parent / LOG_FILE
        entry = f"- {today()} {text.strip()}"
        if path.exists():
            lines = path.read_text(encoding="utf-8").splitlines()
        else:
            lines = [f"# Log - {item.id}", ""]
        first = next((i for i, l in enumerate(lines) if l.startswith("- ")), len(lines))
        lines.insert(first, entry)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
