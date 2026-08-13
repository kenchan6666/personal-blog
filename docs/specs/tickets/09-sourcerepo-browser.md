## Parent

https://github.com/kenchan6666/personal-blog/issues/1

## What to build

For a Published Project with a public SourceRepo, visitors get a GitHub-like read-only browser (README, branch switch, deep tree, file blob) via API. Private repos never expose tree/blob to visitors.

## Acceptance criteria

- [ ] Public SourceRepo supports README, branch switch, deep tree, and blob view
- [ ] Private SourceRepo does not return tree/blob to visitors
- [ ] Draft or non-public Projects cannot be browsed by visitors
- [ ] GitHub API responses may be cached in Redis without storing full repo mirrors

## Blocked by

- #9 (08)
