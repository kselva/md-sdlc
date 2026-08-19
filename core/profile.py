"""
Project resolution - git-style marker discovery.

No central registry of project paths. Each project marks itself with a
.sdlc/config.yml inside its ai-docs/ folder (created by `init`). Resolution
walks up from the current working directory looking for that marker, the
same way `git` walks up looking for `.git/`. No plugin reads .sdlc/config.yml
directly - they all go through resolve_project().
"""
import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

from core.version import __version__

logger = logging.getLogger(__name__)

MARKER_DIR = ".sdlc"
MARKER_CONFIG = "config.yml"


class NotInitializedError(Exception):
    """Raised when no .sdlc/config.yml is found walking up from cwd."""


@dataclass
class Project:
    root: Path            # the ai-docs/ folder itself
    project_prefix: str
    name: str
    marker_version: str | None = None  # tool version that ran `init`, if recorded


def find_marker(start: Path | None = None) -> Path | None:
    """Walk up from start (default: cwd) looking for a .sdlc/ folder. Returns the folder containing it, or None."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / MARKER_DIR / MARKER_CONFIG).exists():
            return candidate
    return None


def resolve_project(start: Path | None = None) -> Project:
    """Find and load the nearest .sdlc/config.yml, or raise NotInitializedError."""
    root = find_marker(start)
    if root is None:
        raise NotInitializedError(
            "not initialized - no .sdlc/ found in this folder or any parent.\n"
            "  Run 'python sdlc_tool.py init' inside your project's ai-docs/ folder first."
        )

    config_path = root / MARKER_DIR / MARKER_CONFIG
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    marker_version = config.get("tool_version")
    if marker_version and marker_version != __version__:
        # stdout, not logger.warning (stderr) - PowerShell 5.1 wraps any stderr
        # output from a native exe into a NativeCommandError/ErrorRecord even at
        # exit code 0, which callers scripting against this CLI can misread as
        # a real failure.
        print(
            f"WARNING - project '{config.get('name', root.name)}' was initialized "
            f"with md_sdlc {marker_version}, running {__version__} - run 'validate' "
            f"after any tool upgrade to confirm nothing changed behavior"
        )

    logger.debug("Resolved project at %s", root)
    return Project(
        root=root,
        project_prefix=config.get("project_prefix", root.name.upper()),
        name=config.get("name", root.name),
        marker_version=marker_version,
    )


def init_marker(target: Path, name: str, project_prefix: str) -> Path:
    """Create .sdlc/config.yml under target. Raises FileExistsError if already initialized."""
    marker_dir = target / MARKER_DIR
    config_path = marker_dir / MARKER_CONFIG
    if config_path.exists():
        raise FileExistsError(f"already initialized: {config_path}")

    marker_dir.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            {"name": name, "project_prefix": project_prefix, "tool_version": __version__},
            f, default_flow_style=False,
        )
    return config_path
