## Parent

https://github.com/kenchan6666/personal-blog/issues/1

## What to build

Owner connects GitHub via OAuth, browses accessible repositories in admin, and attaches a SourceRepo when adding/editing a Project. Public portfolio still only shows Projects explicitly added to the site.

## Acceptance criteria

- [ ] Owner can complete GitHub OAuth and see repository list in admin
- [ ] Owner can attach a SourceRepo to a Project from that list
- [ ] Public site does not list GitHub repos that were never added as Projects
- [ ] OAuth failure fails closed without exposing tokens to the browser beyond the intended flow

## Blocked by

- #6 (05)
