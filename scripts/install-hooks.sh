#!/usr/bin/env bash
# Installs the pre-commit leak-check hook. .git/hooks/ is never tracked by
# git, so this has to be run once after cloning (or re-run if the hook is
# ever lost/reset) - it is NOT automatic on clone.
#
# Usage: scripts/install-hooks.sh
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_PATH="$REPO_ROOT/.git/hooks/pre-commit"

cat > "$HOOK_PATH" <<'EOF'
#!/usr/bin/env bash
# Thin wrapper - the real logic lives in scripts/check-leaks.sh (tracked,
# so it's visible to anyone who clones the repo). This file itself is NOT
# version-controlled (.git/hooks/ never is), so a fresh clone needs it
# reinstalled - see scripts/install-hooks.sh.
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
exec "$REPO_ROOT/scripts/check-leaks.sh"
EOF

chmod +x "$HOOK_PATH"
chmod +x "$REPO_ROOT/scripts/check-leaks.sh"
echo "Installed pre-commit hook at $HOOK_PATH"
