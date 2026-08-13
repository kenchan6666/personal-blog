# Single-VM deploy behind nginx

The public Next.js app, FastAPI (uvicorn), MongoDB, and Redis run on **one VM**, with **nginx** terminating TLS and reverse-proxying to the frontend and API. This favors operational simplicity for a solo Owner portfolio over a split CDN+API topology; scale-out is deferred until traffic or isolation needs justify it.
