#!/usr/bin/env bash
# Scans staged (or, with --all, all tracked) files for internal/private
# names listed in .leakcheck, so they can't reach the public GitHub repo.
#
# Usage:
#   scripts/check-leaks.sh            # check files staged for commit (used by the pre-commit hook)
#   scripts/check-leaks.sh --all      # check every tracked file (manual full-repo audit)
#
# Exit 0 = clean. Exit 1 = found a match, listed below, commit should be blocked.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
LEAKCHECK_FILE="$REPO_ROOT/.leakcheck"

if [ ! -f "$LEAKCHECK_FILE" ]; then
    echo "check-leaks: no .leakcheck file found at $LEAKCHECK_FILE - nothing to check against."
    exit 0
fi

# Build the pattern list, skipping blanks and comments
PATTERNS=$(grep -vE '^\s*(#|$)' "$LEAKCHECK_FILE" || true)
if [ -z "$PATTERNS" ]; then
    echo "check-leaks: .leakcheck has no active patterns."
    exit 0
fi

if [ "${1:-}" = "--all" ]; then
    FILES=$(git -C "$REPO_ROOT" ls-files)
else
    FILES=$(git -C "$REPO_ROOT" diff --cached --name-only --diff-filter=ACM)
fi

if [ -z "$FILES" ]; then
    exit 0
fi

FOUND=0
while IFS= read -r pattern; do
    [ -z "$pattern" ] && continue
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        [ "$file" = ".leakcheck" ] && continue   # the denylist itself legitimately contains these strings
        full_path="$REPO_ROOT/$file"
        [ -f "$full_path" ] || continue
        if grep -Iqi -- "$pattern" "$full_path" 2>/dev/null; then
            echo "LEAK: '$pattern' found in $file"
            FOUND=1
        fi
    done <<< "$FILES"
done <<< "$PATTERNS"

if [ "$FOUND" -eq 1 ]; then
    echo ""
    echo "check-leaks: blocked - one or more internal names would be committed to a public repo."
    echo "Fix the file(s) above, or edit .leakcheck if this is a false positive."
    exit 1
fi

echo "check-leaks: clean."
exit 0
