# CLAUDE.md

Participatory **multi-city** cultural-heritage platform (founding city: **Riobamba, Ecuador**): a **Vue 3 (Vite, TS)** SPA + **Django 5.1 / DRF** API on **PostgreSQL + PostGIS**, with JWT auth, an IEEE-LOM educational layer, geospatial maps, a moderation pipeline, gamification, and optional (Ollama) AI assist. One shared deployment hosts many cities; every geo-scoped record carries a `city` FK. This file is the fast path. A deeper architectural map lives at `docs/PROJECT_MAP.md` (local-only — `docs/` is gitignored); for deploying see [DEPLOY.md](DEPLOY.md).

## The one thing to understand first

Everything is **JWT + `/api/v1/` + PostGIS**, and there are **two run modes** — know which you're in:

| | Local dev | Containers (dev & prod) |
|---|---|---|
| Backend | `manage.py runserver` (`config.settings.development`) | gunicorn (`config.settings.docker`) |
| Frontend | Vite dev server `:5173` (HMR) | static build served by nginx |
| DB | local Postgres+PostGIS | `postgis/postgis:15-3.4` container |
| API base (frontend) | `http://localhost:8000/api/v1` (`.env.development`) | dev `:8080/api/v1` · prod relative `/api/v1` |
| Settings module | `development` | `docker` (NOT `production` — see "Don't break these") |

**Auth is JWT, not sessions.** The SPA stores the access token in `localStorage` and sends `Authorization: Bearer …`; on 401 it clears the token and retries once. No CSRF on API calls.

**Multi-city scoping is request-driven.** The SPA persists the active city slug (`hp_city`) and sends `X-City: <slug>` on every call; `?city=<slug>` wins over the header (`apps/cities/request.py`). List endpoints filter by it, writes are assigned to it, **no city context = unfiltered** (backwards compatible), and detail endpoints deliberately ignore it so cross-city deep links keep working. Cities catalog: `GET /api/v1/cities/`.

## Run it

### Fastest: the dev Docker stack (DB + API + UI, one command)

```bash
cp .env.docker.example .env            # first time only
docker compose up -d --build           # frontend :8080 · API :8080/api/v1 · admin :8080/admin
docker compose logs -f backend
```

The backend entrypoint auto-runs migrate + collectstatic + (by default) creates `admin/admin1234` and seeds heritage data. Optional local AI: `docker compose --profile ai up -d` (pulls an Ollama model).

### Local (host) for snappier iteration

```bash
# Backend — needs a local Postgres+PostGIS DB
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements/development.txt
export DATABASE_URL=postgres://USER:PASS@localhost:5432/heritage_platform_dev
python manage.py migrate
python manage.py seed_heritage          # demo dataset (idempotent)
python manage.py runserver              # :8000  (settings = development)

# Frontend
cd frontend
npm install
npm run dev                             # :5173, talks to :8000/api/v1
```

### Common backend commands

```bash
B="docker exec -it heritageplatform-backend-1"   # dev container name (prod: same, project heritageplatform)
$B python manage.py makemigrations && $B python manage.py migrate
$B python manage.py createsuperuser
$B python manage.py seed_heritage [--reset] [--skip-media-downloads]   # legacy wrapper = seed_city riobamba
$B python manage.py seed_city <slug> [--reset] [--skip-media-downloads] # per-city dataset from data/cities/<slug>.py
$B python manage.py seed_curriculum [--dataset ec_mineduc]  # curriculum-standard catalog from data/curriculum/ (idempotent)
$B python manage.py sync_translation_fields      # after adding a translated field
$B python manage.py check
```

### Frontend commands (in `frontend/`)

```bash
npm run dev      # dev server   |   npm run build   # vue-tsc check + vite build   |   npm run test   # vitest run
```

## Architecture in 60 seconds

```
Vue SPA ──/api/v1/ (JWT)──▶ Django/DRF ──▶ PostgreSQL + PostGIS
                                  └──▶ Ollama (optional, dev profile only)
   nginx also proxies /admin /static /media to the backend
```

- **`City` is the tenancy anchor** (`apps/cities`): `Parish`, `HeritageItem`, `HeritageRoute`, `EducationalResource`, and `LessonPlan` all carry a required `city` FK (existing data was backfilled to Riobamba). `City` carries country/timezone/language + map framing (center/zoom/boundary) + hero image. Users, taxonomies, and gamification stay platform-global.
- **`HeritageItem` is the content hub** (`apps/heritage`): relations, annotations, media, LOM metadata, versions, quality scores, flags, and route stops all reference it. Most entities carry `contributor`/`curator`/`moderator` FKs to `User`.
- **10 Django apps:** `users`, `cities`, `heritage`, `education` (IEEE-LOM), `routes`, `contributions`, `moderation`, `gamification`, `ai_services`, `notifications`.
- **The whole REST surface is one file:** `backend/api/v1/urls.py` (a DRF `DefaultRouter` + a few paths for JWT refresh and AI). Login/register/me are **viewset actions**: `POST /users/login/`, `POST /users/register/`, `GET /users/me/`.
- **Roles are two-tier.** Platform-wide capabilities (Tourist · Contributor · Teacher) live on `UserProfile.role`; **curator/moderator powers are per-city grants** in `cities.CityRole` (staff/superuser are global). Enforcement lives in `apps/users/permissions.py` (`moderation/permissions.py` is a re-export shim); a profile role slug of 'curator' grants nothing by itself. `/users/me` returns `city_roles`. Frontend guards: `requiresAuth`, `requiresCurator` (curator of ANY city — server enforces per-city), `requiresTeacher`.
- **Frontend state:** Pinia stores `auth` / `city` (active city + catalog) / `contributions` / `moderation` / `routes`; API client + per-feature services in `frontend/src/services/api.ts`.

**Key files:** `backend/api/v1/urls.py` (API surface) · `backend/apps/cities/` (City/CityRole, `request.py` city resolution, `seed_city`) · `backend/apps/heritage/models.py` (core models) · `backend/apps/users/permissions.py` (role + per-city permission helpers) · `backend/config/settings/` (env config) · `backend/config/ai.yaml` (AI prompts/model) · `frontend/src/services/api.ts` (axios + auth + X-City) · `frontend/src/stores/city.ts` (active city) · `frontend/src/router/index.ts` (routes + guards) · `frontend/src/components/contribution/ContributionForm.vue` (wizard).

## Don't break these

- **API base is `/api/v1/` and env-driven.** Frontend reads `VITE_API_BASE_URL`; never re-hardcode `http://localhost:8000`. Prod builds with a relative `/api/v1`.
- **Containers use `config.settings.docker`, never `production.py`.** `production.py` forces `SECURE_SSL_REDIRECT=True`, which **loops** behind the TLS-terminating edge nginx. (`manage.py` defaults to `development`, `wsgi.py` to `production` — containers override via `DJANGO_SETTINGS_MODULE`.)
- **PostGIS is mandatory.** Geo models use `PointField`/`LineStringField`/`MultiPolygonField`; the DB must have the PostGIS extension before migrating.
- **Multilingual = django-modeltranslation** (es default, en). Register translated fields in each app's `translation.py` and run `sync_translation_fields` — don't hand-add `name_es`/`name_en` columns. **User-facing strings are Spanish-first** (frontend: `src/i18n/locales/{es,en}.json`).
- **Status workflows are state machines.** HeritageItem & Route: draft → pending → (changes_requested | published | rejected) → archived. Contribution: pending → (approved | rejected | changes_requested).
- **The `X-City`/`?city=` contract is part of the API.** No city context must stay backwards-compatible (unfiltered reads, default-city writes), and detail endpoints must NOT be city-filtered (cross-city deep links). New city-scoped models get a `city` FK + the filter seam in `get_queryset`.
- **`seed_heritage` and `seed_demo_data` command names are docker-entrypoint dependencies** — `seed_heritage` must stay a working wrapper over `seed_city riobamba` (`scripts/seed_city_engine.py` + `data/cities/riobamba.py`).
- **Prod artifacts** (`docker-compose.prod.yml`, `.env.prod*`, `docker/`, `redeploy.sh`) — only touch when changing deployment, not features. **Never commit** `.env` / `.env.prod`.

## Deploy (summary — full details in DEPLOY.md)

Live at **https://heritageplatform.ddns.net** on the shared server `173.249.7.55`, behind a host-level nginx that terminates TLS and routes the hostname → `127.0.0.1:8091`. The server pulls the private repo via a read-only deploy key (`github.com-heritage`).

```bash
# Push to main, then on the server:
cd ~/HeritagePlatform && ./redeploy.sh    # pull + rebuild + restart + scoped prune
```

- **Shared host:** never run host-wide `docker image prune` — it breaks the sibling stacks (`adminweb` on 8081, chatbot on 8090). `redeploy.sh` scopes the prune to project `heritageplatform`.
- **Migrations/collectstatic run automatically** in the backend entrypoint on every start — no manual step after a redeploy.
- **Seeding/superuser are OFF in prod** by default (`.env.prod`). Admin password: `grep DJANGO_SUPERUSER_PASSWORD ~/HeritagePlatform/.env.prod`.

## Gotchas

- **Seed media are placeholders in prod.** `seed_heritage` downloads real media via the **`requests`** lib, which isn't in `requirements/` (only `httpx`). Without it the seeder writes ~70-byte dummy files. For real photos: add `requests` to `requirements/base.txt`, rebuild, re-seed with `--reset`.
- **AI is opt-in.** No provider runs in production; `GET /api/v1/ai/status/` reports availability. Ollama is a **dev-only** compose profile.

## When you finish a change

- **Frontend** → `npm run build` (it type-checks via `vue-tsc`); `npm run test` if you touched tested areas; verify it renders.
- **Backend** → `makemigrations`/`migrate` if models changed; `sync_translation_fields` if you added a translated field; sanity-check the endpoint (`curl …/api/v1/…`); `manage.py check`.
- Keep changes small and match existing patterns. New API fields are a contract — update `frontend/src/types/*` and the serializer together.
