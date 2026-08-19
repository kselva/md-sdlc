"""
Single source of truth for the tool's version.

Bump this on any release. Referenced by --version, every generated
backlog.md (so a stale rollup can be traced to the tool version that made
it), and .sdlc/config.yml (so validate can flag a project marker written by
a materially different tool version).
"""
__version__ = "0.2.0"
