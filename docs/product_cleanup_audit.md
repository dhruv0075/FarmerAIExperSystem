# Core product audit — 2026-10-02

This supersedes the broad original master specification for product scope.
Existing accounts/data and historical modules are preserved; fewer capabilities
are advertised in the normal navigation.

| Feature | Initial classification | Result |
|---|---|---|
| Registration/login/farm profile/settings | WORKING | Retained; saved coordinates used |
| Crop ML | PARTIAL | Genuine saved Random Forest retained; removed static 90% weather match, fallback 95%, universal compatibility labels and unrelated decision ranking from core results; saved recommendation now matches displayed model result |
| Weather | WORKING | Open-Meteo retained; optional charts and advisory link |
| Expert rules/activity confirmation | WORKING | Retained, end-to-end feedback tested |
| Daily plan | PARTIAL | Future activities moved to Upcoming; rain/recent-irrigation conflicts moved to Avoid without changing completion status |
| Lifecycle | PARTIAL | Require actual sowing date; reject future date and unsupported crop; calculate current stage for advice |
| Dashboard | PARTIAL | Removed index/charts overload; crop, stage, weather, main advisory, pending tasks, progress, forecast and history |
| Advisory history | PARTIAL | Added saved farm advisories to History |
| Disease image inference | PLACEHOLDER | Removed unused heuristic image-diagnosis code; no disease inference exposed |
| Problem reports/photos | WORKING | Retained private uploads; contextual symptom/humidity inspection guidance, no diagnosis/confidence |
| Market prices | PARTIAL / external blocker | Cache-only reads, explicit bounded refresh, concurrency guard; provider still unreachable from this machine |
| Market forecasts/sell planner | PARTIAL | Hidden from core UI; no fabricated prices exposed |
| Profit projection/resource discovery | PLACEHOLDER / external blocker | Hidden from core navigation; existing data/routes retained |
| Expense/sales accounting | WORKING | Data/routes preserved, removed from core navigation |
| Comparison/what-if/risk/fertilizer pages | PARTIAL | Removed standalone navigation to keep core workflow focused |
| Research/ML/expert details | WORKING | Consolidated entry with metrics, sources, feedback example and limits; detail links retained |
| Vercel startup | BROKEN | Static-upload import write removed; centralized runtime paths; repository-write guard passes |

## Evidence

- Saved model re-evaluation on documented stratified 80/20 benchmark split:
  accuracy 0.9954545, macro precision 0.9956710, recall 0.9954545, F1 0.9954517.
  Confusion matrix saved in ignored `artifacts/model_revalidation.json`.
  Feature order N/P/K/temperature/humidity/ph/rainfall verified from fitted model.
  This is not independent validation; original dataset provenance/license and
  field/generalization validity remain unverified.
- Fresh Open-Meteo request succeeded on 2026-10-02: ten forecast days returned.
  UI uses seven days. Geolocation runs only on explicit setup/profile actions.
- Government API diagnostic: DNS succeeds; TCP ConnectionRefusedError WinError
  10061; Requests ConnectionError outside sandbox. TLS/HTTP/authentication/JSON
  not reached. Key validity is unverified; no real market sample retrieved.
- Requirements installed. Targeted market, routes, activity feedback, crop and
  lifecycle tests passed before full regression. Final counts recorded below.
- Vercel-style import with AGRIWISE_DATA_DIR=/tmp/agriwise passed, including
  an audit hook rejecting repository writes. No paid infrastructure created.

## Runtime write audit

`db.py`: SQLite and parent directory under configured DB_PATH.
`app.py`: verified photo writes under configured UPLOAD_DIR, only on upload.
`official_market_service.py`: atomic official cache under DATA_DIR.
`resource_service.py`: legacy explicit catalog write under DATA_DIR.
`crop_service.py` / `crop_ml_service.py`: artifact writes only in explicit training
functions, never imported startup or inference. Browser/diagnostic/evaluation
scripts write developer artifacts only when explicitly executed.

## Git commands

Review and push only source/config/tests/docs; .env, databases, photos and caches
are ignored. Do not use force push.

```powershell
git status --short
git diff --check
git diff --stat
git add app.py config.py services templates static/css/style.css tests scripts docs .gitignore
git commit -m "Simplify core farm workflow and support serverless writable storage"
git push origin main
```

These commands describe the publishing sequence, not proof of a completed push
or hosted deployment. See the delivery message for actual Git status.

## Final verification

- Core product audit baseline: `python -m pytest -q` — 35 passed in 16.28 seconds.
- Saved-model evaluation: passed without retraining or overwriting model files.
- Core journey: register/login, location, soil, weather, ML, lifecycle, generated
  irrigation task, confirmed completion, changed advice, problem report, market
  fallback, logout/login and persistent local records passed.
- Browser: 11 core pages HTTP 200; no JavaScript errors; mobile overflow,
  card structure and collapsing navigation checked. Dashboard HTML nesting was
  corrected after visual screenshot inspection.
- Serverless import: passed with repository writes prohibited. This is a Windows
  filesystem-contract simulation, not proof of a deployed Linux/Vercel runtime.
- Known unavailable: official mandi connectivity/key validation, independent crop
  field validation, image diagnosis, durable serverless SQLite/uploads and shared
  refresh coordination across instances. No deployment was performed by this audit.

## Account security hardening — 2026-10-02

- Registration normalizes email case, validates basic email syntax, bounds names,
  and requires an 8–128 character password containing a letter and digit. Passwords
  are stored with Werkzeug password hashing. Duplicate and malformed registrations
  share one generic response; login errors are generic as well.
- Successful registration/login clears pre-auth session state and creates a
  permanent 12-hour session. Production and Vercel always set Secure cookies;
  HttpOnly and SameSite=Lax are enabled. The production secret is required and read
  from `AGRIWISE_SECRET_KEY` at app creation.
- Each user has a random database-backed session token. Existing SQLite schemas
  receive tokens additively; each request verifies both user ID and token and
  clears stale/mismatched cookies before protected route code runs. Password
  changes rotate this token, revoking sessions that share that database.
- All state-changing POSTs use the existing CSRF check. Logout is now POST-only.
  Password change validates the current password, new password and confirmation,
  saves a new hash, then signs out the current browser session.
- Responses set nosniff, frame, referrer, permissions and scoped CSP headers. The
  CSP intentionally does not restrict script/style sources because the existing
  UI depends on external assets and inline code; this is not a full XSS CSP.
- Settings now includes the password-change flow; the disabled language selector
  was removed. The shared navigation logout controls submit CSRF-protected forms.
- Tests cover generic registration errors, normalized duplicate email, secure
  production cookie flags, session lifetime, password change/logout, CSRF logout,
  and cross-farmer activity/report/image ID tampering.

### Deliberate limitations

- Password reset is not offered because no email provider/token delivery is
  configured. No fake reset workflow is exposed.
- There is no shared rate-limit store. Per-process throttling would not reliably
  protect this multi-instance/serverless deployment, so login rate limiting remains
  a production follow-up requiring a shared store.
- Vercel's per-instance SQLite is not shared. A session from a different instance
  fails closed when its account token does not match, but account state and token
  revocation cannot be coordinated across isolated instance databases. Durable
  shared storage is required for cross-instance continuity and global revocation.
- No deployment or Git push was performed. Vercel still needs a deployment from
  this workspace before these source changes affect the hosted site.

## Current workspace verification — 2026-10-02

- `python -m pytest -q`: 45 passed.
- Browser smoke journey: registration, farm setup, 12 authenticated routes,
  password change, old-session logout, re-login, mobile overflow/sidebar checks;
  no JavaScript errors. This is a local isolated database, not production data.
- Production-configured import and `scripts/verify_serverless.py`: passed with
  isolated temporary storage, `AGRIWISE_SECRET_KEY`, secure cookies enabled, and
  the repository-write audit hook.
- Security regression tests: generic duplicate/invalid registration errors,
  normalized email uniqueness, password validation/change, CSRF logout, cookie
  attributes/headers, missing production secret rejection, stale-session and
  reused-ID cross-instance rejection, additive legacy token migration, and
  cross-farmer ID/private image access checks.
- Not verified: hosted deployment, rate limiting through a shared store, revoking
  sessions on other devices, email-based password reset, live market API access,
  independent field validation of the crop dataset, or disease image inference.
