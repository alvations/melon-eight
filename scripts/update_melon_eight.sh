#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 alvations (Melon Lab)
#
# Push an UPDATE from this repo to the melon-eight launch mirror as ONE new commit
# on top of its existing history (unlike launch_melon_eight.sh, which seeds a fresh
# single-commit history). The new commit's tree is the current HEAD, authored
# solely by the owner. Default message: "llm benchmark introduction".
#
# Run it from a clean local clone (after committing your change and `git pull`):
#
#     bash scripts/update_melon_eight.sh                          # message = default
#     bash scripts/update_melon_eight.sh "some other message"     # custom message
#     bash scripts/update_melon_eight.sh --force                  # overwrite main
#
# It never touches your working tree or index: it snapshots HEAD's tree, makes a
# commit on top of melon-eight's current main, and pushes that.

set -euo pipefail

OWNER_NAME="alvations"
OWNER_EMAIL="alvations@gmail.com"
MSG="llm benchmark introduction"
REMOTE_NAME="melon"
REMOTE_URL="https://github.com/alvations/melon-eight.git"

FORCE=""
for a in "$@"; do
  case "$a" in
    --force) FORCE="--force" ;;
    *)       MSG="$a" ;;
  esac
done

git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || { echo "error: not inside a git repository"; exit 1; }

# Point (or re-point) the melon remote at the launch repo.
if git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
  git remote set-url "$REMOTE_NAME" "$REMOTE_URL"
else
  git remote add "$REMOTE_NAME" "$REMOTE_URL"
fi

echo "==> fetching $REMOTE_NAME/main (to commit on top of it)"
PARENT=""
if git fetch -q "$REMOTE_NAME" main 2>/dev/null; then
  PARENT="$(git rev-parse FETCH_HEAD)"
  echo "    parent: $PARENT"
else
  echo "    (no remote main yet; this will be the first commit)"
fi

# The tree to publish = the current committed HEAD (commit + pull before running).
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

echo "==> pushing $COMMIT -> $REMOTE_NAME:main ${FORCE:+(force)}"
git push $FORCE "$REMOTE_NAME" "$COMMIT:refs/heads/main"

echo
echo "==> done. melon-eight main history:"
git --no-pager log "$REMOTE_NAME/main" --format='  %h  %an <%ae>  %s' -n 6
