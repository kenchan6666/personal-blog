## Parent

https://github.com/kenchan6666/personal-blog/issues/1

## What to build

Only the allowlisted Owner can request an email OTP, verify it, and obtain a session to access /admin. Unauthenticated callers cannot mutate portfolio content. OTP and session live as short-lived Redis state with rate limits; mail is sent via SMTP from the configured Owner mailbox.

## Acceptance criteria

- [ ] Requesting OTP for a non-allowlisted email is rejected
- [ ] Valid OTP issues a session usable for Owner-only routes
- [ ] Expired or wrong OTP fails closed
- [ ] Rate limiting prevents OTP spam
- [ ] /admin login UI can complete the OTP flow end-to-end against the API

## Blocked by

- #2 (01)
