#!/usr/bin/env bash
# Apply branch protection to `main`. Requires the repo to be public
# (or a GitHub Pro plan): GitHub rejects protection on free private
# repos with HTTP 403. Run immediately after flipping visibility:
#
#   ./scripts/protect-main.sh [owner/repo]
#
# What it enforces for non-admins: changes land via PR (1 approval,
# stale reviews dismissed, conversations resolved) with the always-on
# `tests` check green and the branch up to date. Force pushes and
# branch deletion are blocked for everyone via the API settings below
# except admins while `enforce_admins` is false — flip that to true in
# the payload if the maintainer should stop direct-pushing too.
set -euo pipefail

REPO="${1:-holmbergf/elt-pipeline}"

gh api --method PUT "repos/${REPO}/branches/main/protection" \
  -H "Accept: application/vnd.github+json" \
  --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["tests"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": true
}
JSON

echo "Branch protection applied to ${REPO}@main:"
gh api "repos/${REPO}/branches/main/protection" \
  --jq '{required_status_checks, enforce_admins: .enforce_admins.enabled, allow_force_pushes: .allow_force_pushes.enabled, allow_deletions: .allow_deletions.enabled, reviews: .required_pull_request_reviews.required_approving_review_count}'
