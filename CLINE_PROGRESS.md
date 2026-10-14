# CLINE_PROGRESS.md — AgriWise AI

Living progress tracker. Statuses: NOT STARTED / IN PROGRESS / IMPLEMENTED /
TESTED / VERIFIED / BLOCKED.

- **IMPLEMENTED** — the code was written.
- **TESTED** — tests were executed and the real result is recorded here.
- **VERIFIED** — evidence supports the behaviour for the stated scope.
- **BLOCKED** — a genuine external constraint prevents completion.

No task is marked VERIFIED without recorded evidence.

---

## Session summary

| Item | Value |
|---|---|
| Date | 2026-10-14 |
| Branch | `main` |
| Last commit at start | `1ee1704` — "Handle stale per-instance farmer sessions" |
| Working tree at start | **Dirty.** Prior agent/user modifications across `app.py`, several services, templates, docs, `static/css/product.css`, `static/js/farm-scene.js`, plus untracked new files. |
| Baseline test result | **134 passed, 0 failed** (75.64s) |
| Final test result | **145 passed, 0 failed** (80.67s) |
| Regression | None |
| Commits made | None (not requested) |
| Destructive commands used | None. No `reset`, `clean`, `stash`, or checkout. No database reset. No file deletion. |

---

## Task tracker

### P0 — Protect and establish the baseline

| Task | Priority | Status | Evidence |
|---|---|---|---|
| Inspect dirty working tree | P0 | VERIFIED | `git status --short --branch` captured before any edit. Staged/unstaged/untracked files recorded. |
| Inspect branch and latest commit | P0 | VERIFIED | Branch `main`, HEAD `1ee1704`. |
| Inspect prior handoff and docs | P0 | VERIFIED | `CLINE_HANDOFF.txt`, `docs/engineering_report.md`, `docs/requirements_audit.md`, `docs/current_baseline.md` read. |
| Establish test baseline | P0 | TESTED | `pytest -q` → 134 passed, 0 failed. |
| Record baseline in tracker | P0 | IMPLEMENTED | This file. |
| Preserve existing work | P0 | VERIFIED | Only additive changes. No existing test weakened or removed. |

### P1 — Core application reliability and security

| Task | Priority | Status | Evidence |
|---|---|---|---|
| Fix internal exception disclosure in `/api/weather` | P1 | TESTED | `app.py` now returns a generic message for non-`WeatherError` exceptions and logs the real one. Covered by `test_weather_api_does_not_leak_internal_exception_text`. |
| Fix internal exception disclosure in `/api/reverse-geocode` | P1 | TESTED | `app.py` returns 502 with a generic message for unexpected exceptions; `ValueError` validation wording is preserved. Covered by `test_reverse_geocode_api_does_not_leak_internal_exception_text`. |
| Verify cross-user data isolation | P1 | TESTED | `test_second_user_cannot_mutate_first_user_activity` — intruder POST does not change owner row. `test_intruder_dashboard_does_not_expose_other_farm_name` passes. |
| Verify session invalidation on password change | P1 | TESTED | `test_password_change_invalidates_existing_sessions`. |
| Verify forged session token rejection | P1 | TESTED | `test_tampered_auth_token_is_rejected`. |
| Verify CSRF enforcement | P1 | TESTED | `test_csrf_token_is_required_for_state_changing_posts`, run with `CSRF_ENABLED=True` to match production. |
| Verify no traceback leakage in protected pages | P1 | TESTED | `test_protected_pages_do_not_render_tracebacks`. |
| Verify API auth requirement | P1 | TESTED | `test_api_endpoints_require_authentication`. |
| Crop prediction path validation | P1 | TESTED | Pre-existing `tests/test_reliability_repairs.py` and `tests/test_ml.py` pass unchanged. |
| Financial calculation determinism | P1 | TESTED | Pre-existing `tests/test_integrity.py` and `tests/test_reliability_repairs.py` pass unchanged. |
| Market integration (mocked) | P1 | TESTED | Pre-existing `tests/test_market_integration.py` passes. Live access remains BLOCKED. |
| Weather timeout/cache/stale handling | P1 | TESTED | Pre-existing `tests/test_weather.py` passes. |


### P1 — UI transformation and accessibility

| Task | Priority | Status | Evidence |
|---|---|---|---|
| Audit existing 3D implementation | P1 | VERIFIED | `static/js/farm-scene.js` implements Three.js field and plant scenes with lazy loading via `IntersectionObserver`, `ResizeObserver` resize handling, `requestAnimationFrame` cleanup, reduced-motion support and a `fallback` state. Used by `templates/index.html` and `templates/crop_lifecycle.html`. |
| Add keyboard skip link | P1 | IMPLEMENTED | `templates/base.html` + `.skip-link` in `static/css/product.css`. |
| Add ARIA live region for flash messages | P1 | IMPLEMENTED | `templates/base.html`: container is `role="status" aria-live="polite"`; errors get `role="alert"`; decorative icons are `aria-hidden`. |
| Add main landmark target | P1 | IMPLEMENTED | `<main id="main-content" tabindex="-1">`. |
| Add non-3D graceful fallback styling | P1 | IMPLEMENTED | CSS rules for `[data-farm-scene][data-scene-state='fallback']`. |
| Full visual redesign | P2 | NOT STARTED | Prior agent work (`product.css`, serif/sans type system, earth palette, hero and lifecycle layouts) already exists and is coherent. A further wholesale redesign was not undertaken because it would risk discarding working, already-reviewed work without evidence of a defect. |
| Browser visual verification | P1 | VERIFIED | `scripts\browser_check.py` executed with exit code 0. 19 page checks all HTTP 200, 0 JavaScript errors, 0 HTTP errors, WebGL field scene `ready`, live Open-Meteo `available`, tablet 768 px and mobile 390 px layout bounds held. Evidence in `artifacts/browser_results.json` and `docs/research/experimental_results.md` E5. |
| Fix stale browser script | P1 | TESTED | The script referenced a removed `no_soil_test` checkbox and failed on first run. Updated to fill the four required soil fields. `tests/test_black_box.py` already asserted that checkbox is absent, confirming the script was the stale artifact. |

### P1 — Testing

| Task | Priority | Status | Evidence |
|---|---|---|---|
| Add security regression suite | P1 | TESTED | `tests/test_security.py`, 11 tests, all passing. |
| Full suite after changes | P1 | TESTED | 145 passed, 0 failed. |
| Test inventory document | P2 | IMPLEMENTED | `docs/test_inventory.md`. |
| Coverage measurement | P2 | BLOCKED | `coverage.py` not installed. |
| Browser automation | P1 | VERIFIED | `scripts\browser_check.py` ran with exit code 0: 19 page checks HTTP 200, 0 JavaScript errors, 0 HTTP errors, WebGL scene `ready`, responsive tablet/mobile bounds held. Evidence in `artifacts/browser_results.json`. |


### P2 — Research

| Task | Priority | Status | Evidence |
|---|---|---|---|
| Inspect and preserve existing research docs | P2 | VERIFIED | `docs/research_gap.md`, `docs/research_evaluation.md`, `docs/data_provenance.md` read and left in place. New files added under `docs/research/` without moving anything. |
| Literature review with verified citations | P2 | IMPLEMENTED | `docs/research/literature_review.md` — two papers, each fetched and read from the publisher or PMC, with title, authors, year, venue and DOI copied from source. |
| Research comparison matrix | P2 | IMPLEMENTED | In `literature_review.md`. Uses "not reported" rather than inventing coverage. |
| Research gap identification with evidence grading | P2 | IMPLEMENTED | `docs/research/research_gap_evidence.md` — separates supported from unestablished gaps. |
| Dataset provenance documentation | P2 | IMPLEMENTED | `docs/research/dataset_provenance.md` — provenance recorded as NOT ESTABLISHED. |
| Reproducible methodology | P2 | IMPLEMENTED | `docs/research/methodology.md` — exact protocol, seed, metrics, software versions. |
| Experimental results | P2 | IMPLEMENTED | `docs/research/experimental_results.md` — real outputs plus an explicit list of experiments not run. |
| Limitations and future work | P2 | IMPLEMENTED | `docs/research/limitations_and_future_work.md`. |
| Paper outline | P2 | IMPLEMENTED | `docs/research/research_paper_outline.md` — marked NOT publication-ready. |
| Reproduce ML experiment | P2 | TESTED | Metrics read from `ml/model_metrics.json` produced by `ml/train_model.py`; also exercised by `tests/test_ml.py`. |

### P2 — Production readiness

| Task | Priority | Status | Evidence |
|---|---|---|---|
| Review secret configuration | P2 | VERIFIED | `config.py` reads `AGRIWISE_SECRET_KEY` from env; `create_app` raises if production has no key. No secret value was printed. |
| Review session cookie configuration | P2 | VERIFIED | `SESSION_COOKIE_HTTPONLY=True`, `SAMESITE=Lax`, `SECURE` in production. Asserted by existing `tests/test_routes.py`. |
| Review security headers | P2 | VERIFIED | `after_request` sets `nosniff`, `DENY`, `Referrer-Policy`, `Permissions-Policy`, restrictive CSP. |
| Document SQLite ephemeral-storage consequence | P2 | IMPLEMENTED | `docs/research/limitations_and_future_work.md` item 19. |
| Production deployment | P2 | NOT DONE | Not requested and not performed. |


---

## Confirmed defects found and fixed

| ID | Severity | Defect | Root cause | Fix | Regression test |
|---|---|---|---|---|---|
| D1 | HIGH | `/api/weather` returned raw `str(exception)` to the client | Bare `except Exception` echoed the message | Generic message for unexpected exceptions; `WeatherError` wording preserved; real error logged server-side | `test_weather_api_does_not_leak_internal_exception_text` |
| D2 | HIGH | `/api/reverse-geocode` returned raw `str(exception)` to the client | Same pattern | `ValueError` → 400 with validation text; anything else → 502 with generic message and server-side log | `test_reverse_geocode_api_does_not_leak_internal_exception_text` |
| D3 | MEDIUM | `scripts/browser_check.py` failed with a Playwright `TimeoutError` waiting for `[name=no_soil_test]` | Test harness was stale: that checkbox was removed when soil values became required, and `tests/test_black_box.py` already asserts its absence | Script now fills the four required soil fields with synthetic values | Re-executed the script; exit code 0 |

## Confirmed limitations (not defects, not fixed)

| ID | Limitation | Reason not fixed |
|---|---|---|
| L1 | Official market API never returned a successful live response | External blocker. No successful HTTP response has been observed. Cannot be fixed in code. |
| L2 | No price forecasting possible | No verified historical price observations exist. |
| L3 | No disease image classifier | No legitimate dataset or model exists. Integrating an unvalidated model would be dishonest. |
| L4 | No notification delivery mechanism | No email/SMS/push integration exists; not claimed. |
| L5 | CSRF disabled under `TESTING` by design | Intentional for tests. Explicitly covered with `CSRF_ENABLED=True`. |
| L6 | Single-process cache locking | Multi-worker shared locking not implemented; documented rather than guessed at. |
| L7 | Dataset provenance unresolved | Cannot be established from the file. Documented, not fabricated. |

---

## Blockers

| Blocker | Impact | Status |
|---|---|---|
| `coverage.py` not installed | No statement or branch coverage figures | Not installed in `.venv`. Not added to `requirements.txt` to avoid changing project dependencies without authorisation. |
| Live official market API | Live market integration unverifiable | Repeated external attempts have failed before authentication. A timeout does not prove the key is invalid. |
| No regional dataset | Geographic/temporal validation impossible | No dataset with a geographic or temporal key and a verifiable licence is available. |

---

## Commands used

```powershell
git status --short --branch
git log --oneline -5 --no-decorate
.venv\Scripts\python.exe -m pytest -q --no-header -p no:cacheprovider
.venv\Scripts\python.exe -m pytest tests/test_security.py -q --no-header -p no:cacheprovider
.venv\Scripts\python.exe -m pip install playwright==1.47.0
.venv\Scripts\python.exe scripts\browser_check.py
```

## Next action

The highest-value remaining work, in order:

1. **Obtain a regional crop dataset with a verifiable licence and a geographic or
   temporal key, then run a proper holdout experiment.** This is the only way to
   convert the 0.9955 local benchmark figure into a defensible claim. See
   `docs/research/methodology.md` for the protocol that is already written.
2. **Expand the literature review to a documented systematic search.** Two papers
   are verified; a related-work section needs more, and the search strings and
   inclusion criteria must be recorded.
3. **Establish live official market access** and record real parsed records.
   Until then market integration stays fixture-tested and BLOCKED.
4. **Install `coverage.py` and measure the critical modules.** Without it no
   coverage figure is claimed anywhere.

Consider also: a farmer user study. It is the only way to evaluate usability or
outcome claims, and it has never been performed.
