# API, security and deployment audit

**Scope:** source/configuration inspection and current route tests. No live
deployment, penetration test, credential check, or external-provider success
claim was made in this audit.

## HTTP interface inventory

The Flask route decorators are in [`app.py`](../../app.py#L385).

### JSON endpoints

| Endpoint | Auth | Source behavior | Status qualification |
|---|---|---|---|
| `GET /healthz` | Public | Executes a local `SELECT 1` and returns status JSON. | Local process/database connectivity only; no provider/model readiness check. |
| `POST /api/reverse-geocode` | Login required | Validates coordinate bounds, calls `reverse_geocode`, returns location or generic 502 for unexpected errors. | Provider results depend on external services; coordinate fallback may be returned. |
| `POST /api/location` | Login required | Validates coordinates and writes to the current user's farm record. | Local DB operation. |
| `GET /api/weather` | Login required | Looks up current farm coordinates and calls weather adapter. | Can return provider/cached weather or unavailable error; modeled forecast, not sensor data. |
| `POST /api/recommend-crop` | Login required | Validates the seven classifier inputs and returns model result/explanation or generic 503. | Requires the saved crop model artifact. |

JSON routes use `login_required` except `/healthz`; protected status is also
covered by [`test_security.py`](../../tests/test_security.py). State-changing
POSTs are subject to the app's CSRF check when enabled.

### Browser workflows with external calls

- `/weather` and farm planning use Open-Meteo forecasts.
- farm setup/reverse geocoding uses Nominatim first and BigDataCloud fallback.
- `/market` reads the official-data adapter cache; `/market/refresh` invokes a
  bounded explicit request.
- disease image screening is local inference and independent from the
  separately stored symptom-report route.

## External integrations

| Service | Implementation | Timeout/cache/fallback | Evidence status |
|---|---|---|---|
| Open-Meteo forecast | [`weather_service.py`](../../services/weather_service.py) | Request timeout 8 seconds; in-memory cache TTL 30 minutes; stale in-memory fallback if refresh fails. | Existing project docs report a live weather response on 2026-09-30; that was a single earlier observation, not a controlled current-session check. Unit tests mock provider behavior. |
| Nominatim | [`location_service.py`](../../services/location_service.py) | Request timeout 5 seconds; 24-hour in-memory reverse-geocode cache; fallback to BigDataCloud and then coordinate text. | Not independently live-checked during this audit. |
| BigDataCloud | [`location_service.py`](../../services/location_service.py) | Request timeout 5 seconds; used only if Nominatim path fails. | Not independently live-checked during this audit. |
| data.gov.in | [`official_market_service.py`](../../services/official_market_service.py) | Connect/read timeout `(3.05, 5)` seconds, at most 3 tries, process-local lock/cooldowns/cache, 10-record sample per request, cached file writes after successful parse. | A previous documented diagnostic reached DNS/TCP/TLS then timed out waiting for HTTP. Key acceptance, response format and usable records are **unverified**. |
| CDN map/chart/framework assets | Templates and static JavaScript/CSS. | Requires browser network access for third-party assets where CDN references are used. | Browser results recorded in older documents predate the latest homepage redesign; not repeated for this audit. |

The market adapter filters and validates returned records and does not treat
`data/market_data.json` as provider evidence. A small sample request does not
constitute a complete nationwide price feed. The official adapter's
coordination/cache is process-local and not shared among workers or serverless
instances.

## Security controls observed in source

Controls are implementation evidence, not a certification or complete
security assessment.

| Area | Observed control | Evidence / limit |
|---|---|---|
| Passwords | Werkzeug password-hash helpers used on register/login/password-change. | [`app.py`](../../app.py#L418). No password-reset/email-verification flow was established in this audit. |
| Authentication | Flask session stores user ID and auth token; current-user lookup matches both against DB. Sessions are cleared at login/logout; password change rotates token. | [`get_current_user`](../../app.py#L176), login/logout/settings routes. |
| Session cookie | HttpOnly, SameSite=Lax, 12-hour permanent session; Secure in production or when configured. Production requires `AGRIWISE_SECRET_KEY`. | [`create_app`](../../app.py#L302). Local default key is generated at runtime; production check prevents starting without configured secret. |
| CSRF | Per-session random token, `secrets.compare_digest`, hidden template fields/header support; POST check enabled unless testing or explicitly overridden. | [`load_global_context`](../../app.py#L336), `CSRF_ENABLED` config. Tests cover rejection of a bad token. |
| Headers | `nosniff`, `DENY`, strict-origin referrer policy, restricted Permissions Policy, CSP directives for `base-uri`, `object-src`, `frame-ancestors`. | `set_security_headers` at [`app.py`](../../app.py#L324). This is not a comprehensive restrictive script/style CSP. |
| SQL | Inspected authentication and core data queries use SQLite parameter binding. | Route/service source; not a proof that every SQL statement is injection-free. |
| Upload validation | JPEG/PNG/WebP allowlist; MIME and decoded image format checks; 5 MiB image limit; 24M-pixel dimension ceiling; `secure_filename` plus UUID prefix for saved reports. | [`disease_detection_page`](../../app.py#L1118), [`report_problem_page`](../../app.py#L1212). |
| Upload access | Report images are retrieved through an authenticated route with report ownership lookup; direct static upload path is blocked. | `/disease-image/<report_id>` and `load_global_context`; review route before production changes. |
| Error disclosure | Unexpected JSON API errors are logged server-side and replaced with generic response text in the inspected location/weather/recommendation handlers. | [`app.py`](../../app.py#L1860); regression checks in `test_security.py`. |
| Secrets | Environment variables are read for secret/API key. `.env` is ignored; `.env.example` is a blank placeholder per existing docs. | `config.py`, `render.yaml`, `.gitignore`. Secret values were not opened or included in the audit. |
| Rate limiting | No application rate-limiter was identified in inspected config/dependencies/routes. | Treat as an unverified control gap, not a demonstrated exploit. |

No third-party penetration test, dependency-vulnerability scan, threat model
review, production configuration check or full access-control proof was run.

## Data and privacy considerations

The local app persists personal account/farm information and farmer-submitted
crop records in SQLite. Optional disease report photos are kept under the
configured private upload directory and are served through an authorized
route. Provider requests may transmit user farm coordinates to external
weather/geocoding services. The code and docs should be accompanied by an
appropriate user notice and retention policy before real deployment; this
audit did not inspect live user records.

## Deployment configurations found

### Render Blueprint

[`render.yaml`](../../render.yaml) configures one paid Starter instance, one
1 GB persistent disk at `/var/data`, Gunicorn with one worker/four threads,
production cookie settings and generated secret, plus optional market API key.
The single-instance restriction preserves process-local market coordination.
The YAML describes a deployment option; it does not prove a service was
created, billed or verified.

### Vercel demonstration

[`docs/vercel.md`](../vercel.md) describes Flask auto-detection and data paths
under `/tmp/agriwise`. `/tmp` is ephemeral and not shared across instances, so
SQLite user data/uploads are not durable there. A Git push does not migrate the
local farmer database. The document also warns not to train during deployment.
No live deployment is verified by this audit.

### Local development

`config.py` selects the repository data directory by default and uses
`AGRIWISE_DATA_DIR` when configured; `VERCEL` changes the default to a
temporary directory. `db.init_db` initializes the selected SQLite path at
startup. The configured paths must be reviewed carefully before running
operations that create or mutate data.

## Readiness assessment

- **Local prototype:** source and tests establish working Flask routes and
  temporary-database testability.
- **Hosted, durable farmer service:** not established. Choose a persistent
  storage architecture, verify upload protections/backups, assess privacy and
  threat model, validate external provider behavior from the hosting region,
  and verify real deployment health before claiming production readiness.
- **Market integration:** configured but live data usability remains
  unverified; do not promise operational market coverage.
- **Model service:** artifact existence does not prove deployment dependency
  installation or successful hosted inference.
