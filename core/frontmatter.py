"""
Frontmatter parse/write.

Pure serialization only - no business logic, no vocabulary validation.
Mirrors the separation jira_client.py keeps between HTTP mechanics and
ticket semantics: this module knows nothing about Epic/Story/Task.
"""
import frontmatter as fm


def parse(file_path) -> tuple[dict, str]:
    """Read a markdown file, return (frontmatter_dict, body_text)."""
    post = fm.load(file_path)
    return dict(post.metadata), post.content


def write(file_path, metadata: dict, body: str) -> None:
    """Write a markdown file with the given frontmatter dict and body text."""
    post = fm.Post(body, **metadata)
    # sort_keys=False keeps the header in the order it was written - without
    # it every tool write reshuffles a hand-written header (0.4.0 fix).
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(fm.dumps(post, sort_keys=False))
