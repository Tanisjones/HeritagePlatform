# Deployment — Heritage Platform at `https://heritageplatform.ddns.net`

Production deployment of this app (Django + Vue 3 + PostgreSQL/PostGIS), deployed on
the shared server `173.249.7.55` with the **same structure** as the sibling stacks
already running there (`adminweb`, and the chatbot at `mates.ddns.net`).

## Architecture on the server (`173.249.7.55`)

A single **host-level nginx** owns ports 80/443 and routes by hostname to each app's
local-only container. This stack adds one more hostname/port pair:

```
                   ┌──────────────────────────── host nginx (:80/:443) ───────────────────────────────┐
  Internet ──────▶ │  heritageplatform.ddns.net ──TLS──▶ 127.0.0.1:8091 (this app's nginx container)   │
                   │  mates.ddns.net            ──TLS──▶ 127.0.0.1:8090 (chatbot nginx)                 │
                   │  173.249.7.55 / *          ───────▶ 127.0.0.1:8081 (adminweb nginx, HTTP by IP)    │
                   └────────────────────────────────────────────────────────────────────────────────────┘

  this app (docker-compose.prod.yml):
    frontend (nginx) 127.0.0.1:8091 ─▶ serves Vue build, proxies /api /admin /static /media
        └─▶ backend (gunicorn + WhiteNoise) :8000 ─▶ db (postgis, private volume)
```

- TLS for `heritageplatform.ddns.net` is issued by **host certbot** (Let's Encrypt) with auto-renew.
- Only `frontend` publishes a port, and only on `127.0.0.1` — nothing in this stack is
  reachable from the internet except through the host nginx, i.e. only via the hostname.
- Auth is **JWT** (Authorization header), so the SPA works over the edge HTTPS without
  secure-cookie gymnastics. Settings module is `config.settings.docker` (production-like,
  but no forced HTTPS redirect — the edge terminates TLS).

## Files

| File | Purpose |
|------|---------|
| `docker-compose.prod.yml` | Production stack: `db` (PostGIS), `backend` (gunicorn), `frontend` (nginx). Publishes `127.0.0.1:8091` only. |
| `docker/backend/Dockerfile` | Django + GeoDjango image. Entrypoint runs migrate + collectstatic on every start. |
| `docker/backend/entrypoint.sh` | Waits for DB, migrates, collectstatic, optional superuser/seed, then gunicorn. |
| `docker/frontend/Dockerfile` | Multi-stage: Vite build → nginx serving `dist`. |
| `docker/frontend/nginx.conf` | App-internal nginx: SPA + proxy to backend + `/static` `/media`. |
| `.env.prod.example` | Template for `.env.prod` (the real file is gitignored). |
| `redeploy.sh` | Pull + rebuild + restart + scoped image prune. |

The Dockerfiles are **shared with the dev stack** (`docker-compose.yml`). Production
differs only in `docker-compose.prod.yml`: locked-down env, localhost-only publish,
healthchecks, and the Vue bundle built with a same-origin `VITE_API_BASE_URL=/api/v1`.
The dev stack (host-published `:8080`, optional Ollama profile) is unchanged.

## First-time deploy

On the server, as user `jduch`:

```bash
# 1. Clone via the deploy key (see "Deploy key" below for key setup).
git clone git@github.com-heritage:Tanisjones/HeritagePlatform.git ~/HeritagePlatform
cd ~/HeritagePlatform

# 2. Create the production env file from the template and fill in secrets.
cp .env.prod.example .env.prod
#   - SECRET_KEY:         python3 -c "import secrets; print(secrets.token_urlsafe(64))"
#   - POSTGRES_PASSWORD:  a strong password
#   (optionally seed demo data on the first boot: set SEED_HERITAGE_DATA=true)
nano .env.prod

# 3. Build & start. Migrations + collectstatic run automatically in the entrypoint.
docker compose -p heritageplatform -f docker-compose.prod.yml --env-file .env.prod up -d --build

# 4. Create an admin user (CREATE_SUPERUSER defaults to false in prod).
docker compose -p heritageplatform -f docker-compose.prod.yml --env-file .env.prod \
    exec backend python manage.py createsuperuser
```

The host nginx vhost for `heritageplatform.ddns.net` and the TLS cert are set up once
(see "Edge nginx" below).

## Redeploy (after pushing new code)

Use the helper script — it pulls `main`, rebuilds, restarts, and prunes (scoped). Migrations
run automatically inside the backend entrypoint:

```bash
cd ~/HeritagePlatform && ./redeploy.sh
```

Equivalent manual steps, if you prefer:

```bash
cd ~/HeritagePlatform
git pull
docker compose -p heritageplatform -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

## Deploy key (GitHub → server, read-only)

A dedicated SSH key authorizes the server to pull this private repo, exactly like the
chatbot's `github.com-chatbot` alias:

- Private half lives on the server at `~/.ssh/heritage_deploy` (never leaves it).
- Public half is added to the GitHub repo as a **read-only Deploy Key**.
- `~/.ssh/config` maps a host alias so git uses that key:

  ```
  Host github.com-heritage
      HostName github.com
      User git
      IdentityFile ~/.ssh/heritage_deploy
      IdentitiesOnly yes
  ```

  → clone/pull URL: `git@github.com-heritage:Tanisjones/HeritagePlatform.git`

Generate the key on the server and add the `.pub` to GitHub → repo → Settings → Deploy keys:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/heritage_deploy -C "heritage-deploy" -N ""
cat ~/.ssh/heritage_deploy.pub   # paste into GitHub Deploy keys (read-only)
```

## Edge nginx (host) — set up once

The DDNS record `heritageplatform.ddns.net` must point at `173.249.7.55`. Then add a
host nginx site (config lives at `/etc/nginx/sites-available/`, symlinked into
`sites-enabled/`):

```nginx
# /etc/nginx/sites-available/heritageplatform
server {
    listen 80;
    server_name heritageplatform.ddns.net;

    # Lets certbot serve the ACME challenge; everything else → HTTPS.
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    server_name heritageplatform.ddns.net;

    # Filled in by `certbot --nginx` (ssl_certificate / ssl_certificate_key).

    # Match the app nginx so large media uploads pass through the edge too.
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8091;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable it and obtain the cert:

```bash
sudo ln -s /etc/nginx/sites-available/heritageplatform /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d heritageplatform.ddns.net   # installs cert + auto-renew timer
```

This mirrors the chatbot's edge vhost; the bare-IP `default_server` (adminweb) and the
`mates.ddns.net` vhost are untouched.

## Notes

- **Shared host — never run host-wide `docker image prune`.** It would drop dangling
  images the sibling stacks (`adminweb`, chatbot) depend on and restart them. `redeploy.sh`
  scopes the prune to `com.docker.compose.project=heritageplatform`.
- **Logs:** `docker compose -p heritageplatform -f docker-compose.prod.yml --env-file .env.prod logs -f backend`
- **Migrations / collectstatic** run automatically on every container start (entrypoint),
  so a plain `redeploy.sh` is enough after a schema change — no manual migrate step.
- **Seeding:** `SEED_HERITAGE_DATA` / `SEED_DEMO_DATA` are **off** by default in prod. Turn
  `SEED_HERITAGE_DATA=true` on for a first boot if you want demo content, then set it back.
  Never set `SEED_HERITAGE_RESET=true` against real data — it wipes the seeded tables.
- **DB backups:** data lives in the `postgres_data` named volume. Back it up with
  `docker compose -p heritageplatform -f docker-compose.prod.yml --env-file .env.prod exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup.sql`.
- **AI provider:** the backend reads its AI config from `AI_CONFIG_PATH`
  (`/app/backend/config/ai.yaml`). The optional local Ollama container is a **dev-only**
  profile and is not part of this production stack.
