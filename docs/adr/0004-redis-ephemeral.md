# Redis as cache and ephemeral state

Redis holds short-lived data: Owner OTP codes/sessions, rate limits, and GitHub API response caches. MongoDB (Beanie) remains the system of record for Portfolio entities. Redis is **not** the primary concurrency or business-data layer.
