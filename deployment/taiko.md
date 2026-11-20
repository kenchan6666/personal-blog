# bachi-motion on kenchan0522.blog (`/taiko/`)

This is prepared only. Do not deploy until the bachi-motion Docker PR is
merged (or you intentionally build from that branch) and you are ready to
enable the service. Existing `start.sh --prod --pull` deploys stay as they
are: the `taiko` service uses a Compose profile and is off by default, so
CI can keep pulling `api` / `agent` / `web` from Artifact Registry without
failing on a missing taiko image.

## Why a path, not a subdomain

Asset URLs in bachi-motion are already relative (`js/…`, `assets/…`,
`fetch("samples/…")`), so the app works under a sub-path with no code
change. `https://kenchan0522.blog/taiko/` reuses the existing
Let's Encrypt cert and DNS. A subdomain such as `taiko.kenchan0522.blog`
would need a new DNS record, a certificate SAN or a second cert, and
certbot/nginx server-block changes; path routing is enough here.

nginx strips the `/taiko/` prefix and proxies to the `taiko` container
on port 8080. `/taiko` redirects to `/taiko/`. The `/taiko/` location
repeats the site security headers and loosens CSP just enough for the
Google Fonts the app loads (`fonts.googleapis.com` / `fonts.gstatic.com`).
Do not add other `add_header` lines in `proxy.inc` locations that should
keep inheriting `ssl.conf`.

The in-browser app is static. CLI export (`render.js` + headless Chrome)
is not part of this service.

## Image source (and what changes when the repo is private)

Preferred, and what this Compose file defaults to: **build from a local
checkout** next to this repo, pinned to a commit (`TAIKO_REF`, defaulting to
`a63bf58ef12b25ab19b4297c3fae9f2a9e7d6270` on the bachi-motion
`chore/docker-static` branch, which adds the Dockerfile; after that
PR is merged, bump `TAIKO_REF` to the merge commit on `main`).

```bash
# On the VM, once; not committed.
git clone git@github.com:kenchan6666/bachi-motion.git ../bachi-motion
# or: git clone https://github.com/kenchan6666/bachi-motion.git ../bachi-motion
git -C ../bachi-motion fetch --all --tags
git -C ../bachi-motion checkout "$TAIKO_REF"
```

Override the context with `TAIKO_CONTEXT` if the checkout is elsewhere.
`pull_policy` defaults to `never`, so `docker compose pull` will not look
the image up on a registry.

After `kenchan6666/bachi-motion` is made private:

- Local build still works if this machine can `git pull` the private repo.
  Use a deploy key or a HTTPS token with `repo` scope. Store it in the
  VM's git/ssh config, **not** in `deployment/.env` or this repository.
- To pull a pre-built image instead:
  - **Artifact Registry** (same as `api` / `agent` / `web`): set
    `TAIKO_IMAGE=${IMAGE_REGISTRY}/taiko:<sha>` and
    `TAIKO_PULL_POLICY=always` (or `missing`). Reuses the existing
    `AR_TOKEN` login in `start.sh`. Add a build-and-push job only once
    the image exists; do not add it to the deploy matrix before then.
  - **GHCR** (`ghcr.io/kenchan6666/bachi-motion:<sha>`): `docker login
    ghcr.io` with a PAT or fine-grained token that has `read:packages`,
    and grant that identity package read access. A public package needs
    no auth; a private package does.

Do not put tokens in `deployment/.env` unless you already treat that
file as the sole secret store and you are sure they will not be printed
in logs.

## Enable it later (exact steps)

1. Merge the bachi-motion Docker PR (Dockerfile + `.dockerignore` +
   `docker/nginx.conf`) and note the merged commit SHA.
2. Merge this blog PR. That only adds the route and the optional
   service; the production stack does not start `taiko` yet.
3. On the VM, update the blog checkout (`git pull --ff-only` as the
   usual deploy already does, or wait for the next CI deploy).
4. Clone or update `../bachi-motion` and check out that SHA
   (`TAIKO_REF=<sha>`).
5. Start the profile **once**, after a normal site pull or as a
   recovery build:

   ```bash
   export COMPOSE_PROFILES=taiko
   export TAIKO_REF=<merged-bachi-motion-sha>
   # Recovery / first time (builds taiko locally):
   bash deployment/start.sh --prod
   # Or, after a registry image exists:
   #   TAIKO_IMAGE=… TAIKO_PULL_POLICY=always \
   #   IMAGE_TAG=<blog-sha> bash deployment/start.sh --prod --pull
   ```

   `start.sh` / `start.ps1` only build or pull `taiko` when
   `COMPOSE_PROFILES` includes `taiko`. Leaving the variable unset keeps
   today's CI path (`IMAGE_TAG=<sha> bash deployment/start.sh --prod
   --pull`) unchanged.

6. Confirm `https://kenchan0522.blog/taiko/` and
   `https://kenchan0522.blog/taiko/js/app.js` return 200. The rest of
   the site (`/zh-Hant`, `/api/health`) should be unaffected.

To stop the service later: start the stack without `COMPOSE_PROFILES=taiko`
(the `/taiko/` route will 502 until the profile is on again).

The container is limited to 64 MiB RAM and 0.25 CPU. Bump those only if
needed; it is a static nginx and should stay small.
