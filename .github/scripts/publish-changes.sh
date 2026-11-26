#!/usr/bin/env bash
set -euo pipefail

repo=$1
message=$2
shift 2

git -C "$repo" add -- "$@"
if git -C "$repo" diff --cached --quiet; then
  exit 0
fi

base=$(git -C "$repo" rev-parse HEAD)
git -C "$repo" -c user.name='github-actions[bot]' \
  -c user.email='github-actions[bot]@users.noreply.github.com' commit -m "$message"

for attempt in 1 2 3 4 5; do
  if git -C "$repo" push origin HEAD:refs/heads/main; then
    exit 0
  fi

  git -C "$repo" fetch origin main
  upstream=$(git -C "$repo" rev-parse FETCH_HEAD)
  if ! git -C "$repo" merge-base --is-ancestor "$base" "$upstream"; then
    echo "::error::$repo/main history changed. Rerun from the current branch tip."
    exit 1
  fi
  if ! git -C "$repo" diff --quiet "$base" "$upstream" -- "$@"; then
    echo "::error::$repo/main changed the files being published. Rerun from the current branch tip."
    exit 1
  fi
  if [[ "$attempt" == 5 ]]; then
    break
  fi
  git -C "$repo" -c user.name='github-actions[bot]' \
    -c user.email='github-actions[bot]@users.noreply.github.com' rebase "$upstream"
  sleep "$attempt"
done

echo "::error::Could not push changes to $repo/main after 5 attempts."
exit 1
