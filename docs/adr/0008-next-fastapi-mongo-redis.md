# Stack: Next.js frontend + FastAPI/Mongo/Redis on one VM

Visitor and Owner UIs are a **Next.js** app (i18n shell: default `zh-Hant`, plus `en`; light liquid-glass UI per ADR-0009). The API is **FastAPI + uvicorn** with **MongoDB/Beanie** as the system of record and **Redis** for OTP/session and GitHub API cache. Process topology is **single VM + nginx** (ADR-0003). This matches the Owner’s stated stack while scoping Redis to ephemeral concerns (ADR-0004).
