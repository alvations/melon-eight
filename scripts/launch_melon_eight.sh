#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
#
# Launch-day mirror: publish the CURRENT working tree to the melon-eight repo as a
# SINGLE, history-free commit, authored solely by the owner, with exactly the
# launch message. No dev history, no co-authors, no trailers.
#
# Run it from inside a clean local clone of this repo (after `git pull`):
#
#     bash scripts/launch_melon_eight.sh            # push (fails if remote main exists)
#     bash scripts/launch_melon_eight.sh --force    # overwrite melon-eight main
#
# It creates a temporary orphan branch, commits the whole tree once as
# "alvations", pushes it to melon-eight's main, then returns you to the branch you
# were on and deletes the temp branch. Your real history is never touched.

set -euo pipefail

OWNER_NAME="alvations"
OWNER_EMAIL="alvations@gmail.com"
MSG="Launch day #sixseven #melonlab"
REMOTE_NAME="melon"
REMOTE_URL="https://github.com/alvations/melon-eight.git"
TMP_BRANCH="launch"

FORCE=""
[ "${1:-}" = "--force" ] && FORCE="--force"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || { echo "error: not inside a git repository"; exit 1; }

# Where to come back to (branch name, or a detached-HEAD sha).
ORIG_REF="$(git symbolic-ref --short -q HEAD || git rev-parse HEAD)"

# On any exit, make sure we don't strand the user on the temp orphan branch.
cleanup() { git checkout -q "$ORIG_REF" 2>/dev/null || true; }
trap cleanup EXIT

# Warn (do not block) on a dirty tree: the mirror will include whatever is present.
if [ -n "$(git status --porcelain)" ]; then
  echo "note: working tree has uncommitted changes; they WILL be included in the mirror."
fi

# Drop any stale temp branch from a previous run.
git rev-parse --verify -q "$TMP_BRANCH" >/dev/null 2>&1 && git branch -D "$TMP_BRANCH"

echo "==> building single-commit history from the current tree"
git checkout -q --orphan "$TMP_BRANCH"
git add -A
git -c user.name="$OWNER_NAME" -c user.email="$OWNER_EMAIL" \
    commit -q --author="$OWNER_NAME <$OWNER_EMAIL>" -m "$MSG"

echo "==> pointing '$REMOTE_NAME' at $REMOTE_URL"
if git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
  git remote set-url "$REMOTE_NAME" "$REMOTE_URL"
else
  git remote add "$REMOTE_NAME" "$REMOTE_URL"
fi

echo "==> pushing to $REMOTE_NAME:main ${FORCE:+(force)}"
git push $FORCE "$REMOTE_NAME" "$TMP_BRANCH:main"

# Success: return to the original ref and drop the temp branch.
git checkout -q "$ORIG_REF"
git branch -D "$TMP_BRANCH" >/dev/null

echo
echo "==> done. melon-eight main now has exactly:"
git --no-pager log "$REMOTE_NAME/main" \
  --format='%H%n  author:    %an <%ae>%n  committer: %cn <%ce>%n  %s'
echo
echo "Expected: ONE commit, subject \"$MSG\", author AND committer = $OWNER_NAME."
