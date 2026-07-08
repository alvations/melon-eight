#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
#
# One-shot sync: PULL the latest from this repo (hallway8 origin), then PUSH that
# state to the melon-eight launch mirror as ONE new commit on top of its history,
# authored solely by the owner. Use this whenever you want melon-eight to catch up
# to hallway8.
#
#   bash scripts/sync_melon_eight.sh                       # message = default
#   bash scripts/sync_melon_eight.sh "coach audio + i18n"  # custom message
#   bash scripts/sync_melon_eight.sh --force               # overwrite mirror main
#
# It pulls your current branch from origin (with retry/backoff), then snapshots
# HEAD's tree and commits it onto melon-eight main via commit-tree, so your working
# tree and index are never touched.

set -euo pipefail

OWNER_NAME="alvations"
OWNER_EMAIL="alvations@gmail.com"
MSG="Sync latest from hallway8"
ORIGIN="origin"
MELON="melon"
MELON_URL="https://github.com/alvations/melon-eight.git"

FORCE=""
for a in "$@"; do
  case "$a" in
    --force) FORCE="--force" ;;
    *)       MSG="$a" ;;
  esac
done

git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || { echo "error: not inside a git repository"; exit 1; }

BRANCH="$(git symbolic-ref --short -q HEAD || true)"
[ -n "$BRANCH" ] || { echo "error: detached HEAD; check out a branch first"; exit 1; }

# --- 1. pull the latest from hallway8 (origin), with retry/backoff ------------
echo "==> pulling $ORIGIN/$BRANCH"
n=0
until git pull --ff-only "$ORIGIN" "$BRANCH"; do
  n=$((n+1)); [ "$n" -ge 4 ] && { echo "error: pull failed after retries"; exit 1; }
  d=$((2**n)); echo "   pull failed; retrying in ${d}s..."; sleep "$d"
done

# --- 2. point (or re-point) the melon remote ---------------------------------
if git remote get-url "$MELON" >/dev/null 2>&1; then
  git remote set-url "$MELON" "$MELON_URL"
else
  git remote add "$MELON" "$MELON_URL"
fi

echo "==> fetching $MELON/main (to commit on top of it)"
PARENT=""
if git fetch -q "$MELON" main 2>/dev/null; then
  PARENT="$(git rev-parse FETCH_HEAD)"
fi

# --- 3. commit HEAD's tree onto melon main, authored by the owner ------------
TREE="$(git rev-parse "HEAD^{tree}")"
echo "==> building commit \"$MSG\" as $OWNER_NAME"
if [ -n "$PARENT" ]; then
  COMMIT="$(GIT_AUTHOR_NAME="$OWNER_NAME" GIT_AUTHOR_EMAIL="$OWNER_EMAIL" \
            GIT_COMMITTER_NAME="$OWNER_NAME" GIT_COMMITTER_EMAIL="$OWNER_EMAIL" \
            git commit-tree "$TREE" -p "$PARENT" -m "$MSG")"
else
  COMMIT="$(GIT_AUTHOR_NAME="$OWNER_NAME" GIT_AUTHOR_EMAIL="$OWNER_EMAIL" \
            GIT_COMMITTER_NAME="$OWNER_NAME" GIT_COMMITTER_EMAIL="$OWNER_EMAIL" \
            git commit-tree "$TREE" -m "$MSG")"
fi

# --- 4. push, with retry/backoff ---------------------------------------------
echo "==> pushing to $MELON:main ${FORCE:+(force)}"
n=0
until git push $FORCE "$MELON" "$COMMIT:refs/heads/main"; do
  n=$((n+1)); [ "$n" -ge 4 ] && { echo "error: push failed after retries"; exit 1; }
  d=$((2**n)); echo "   push failed; retrying in ${d}s..."; sleep "$d"
done

echo
echo "==> done. melon-eight main history:"
git --no-pager log "$MELON/main" --format='  %h  %an <%ae>  %s' -n 6
