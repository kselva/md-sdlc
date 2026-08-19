"""
Shared pytest fixtures - builds a minimal Epic/Story tree under tmp_path so
each test gets an isolated repo instead of sharing tests/fixtures/ state.
"""
import argparse
from pathlib import Path

import pytest

from core.repo import AiDocsRepo


def write_story(root: Path, story_id: str = "STORY-01-test-story", status: str = "in-progress") -> Path:
    epic_dir = root / "EPIC-T1-test-epic"
    story_dir = epic_dir / story_id
    story_dir.mkdir(parents=True)

    (epic_dir / "epic.md").write_text(
        "---\nid: EPIC-T1-test-epic\ntype: epic\nkind: work-item\nstatus: in-progress\n"
        "owner: Selva\nupdated: 2026-08-18\n---\n\n# Test Epic\n",
        encoding="utf-8",
    )
    (story_dir / "story.md").write_text(
        f"---\nid: {story_id}\ntype: story\nkind: work-item\nstatus: {status}\n"
        f"parent: EPIC-T1-test-epic\nowner: Selva\nupdated: 2026-08-18\nscenario: feature\n---\n\n"
        f"# Test Story\n",
        encoding="utf-8",
    )
    return story_dir


def write_review_md(story_dir: Path, rows: list[tuple[str, str, str, str, str, str]]) -> None:
    header = "# Review Findings\n\n| id | severity | status | summary | reported_by | updated |\n|----|----------|--------|---------|--------------|---------|\n"
    body = "".join(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |\n" for r in rows)
    (story_dir / "review.md").write_text(header + body, encoding="utf-8")


@pytest.fixture
def repo(tmp_path) -> AiDocsRepo:
    return AiDocsRepo(tmp_path)


@pytest.fixture
def make_args():
    def _make(**kwargs) -> argparse.Namespace:
        return argparse.Namespace(**kwargs)
    return _make
