# Test inventory

Every row records an actual executed suite or script, not an intention. "Not
run" is stated explicitly where applicable.

## Execution environment

Python 3.12.4, Flask 3.0.3, scikit-learn 1.5.1, pandas 2.2.2, numpy 2.0.2,
pytest 8.3.2. Platform: Windows, PowerShell. All tests use disposable SQLite
databases under `tmp_path`; the farmer database `database.db` is never touched
by any test.

## 1. Consolidated result

| Suite | Command | Result |
|---|---|---|
| Full automated suite | `.venv\Scripts\python.exe -m pytest -q --no-header -p no:cacheprovider` | **145 passed, 1 warning, 0 failed** in 80.67s |
| Security suite (new) | `.venv\Scripts\python.exe -m pytest tests/test_security.py -q --no-header -p no:cacheprovider` | **11 passed** in ~15s |
| Browser automation | `.venv\Scripts\python.exe scripts\browser_check.py` | See "Browser automation" below |

Baseline before this work session: 134 passed. Delta: +11 security tests. No
existing test was modified, weakened or deleted.

The single warning is environmental (joblib cannot count physical cores on this
Windows host) and is not an application defect.

## 2. Suite-by-suite inventory

| File | Category | Purpose | Status |
|---|---|---|---|
| `tests/test_security.py` | Security, white-box, regression | Error disclosure, cross-user isolation, session invalidation, forged tokens, CSRF, traceback leakage | **11 passed (new)** |
| `tests/test_black_box.py` | Black-box, boundary, equivalence partition | Registration partitions, negative inputs, workflow state changes, upload validation, weather failure paths | Passed (pre-existing) |
| `tests/test_reliability_repairs.py` | White-box, service-level | `validate_crop_inputs` boundaries, JSON API error contracts, market history scoping, expense validation, activity idempotency | Passed (pre-existing) |
| `tests/test_integrity.py` | Data integrity, integration | Real HTML finance field names, invalid image rejection, resource submission persistence, CSRF | Passed (pre-existing) |
| `tests/test_market_integration.py` | Integration, market adapter | Fixture-driven parsing, caching, freshness states, filtering, deduplication | Passed (pre-existing) |
| `tests/test_ml.py` | ML evaluation | Training produces model and metrics; prediction interface | Passed (pre-existing) |
| `tests/test_weather.py` | Service, error paths | Open-Meteo parsing, timeout, cache fallback, stale labelling | Passed (pre-existing) |
| `tests/test_rules.py` | White-box, expert system | IF-THEN rule firing and conflict handling | Passed (pre-existing) |
| `tests/test_lifecycle.py` | Service, lifecycle math | Stage calculation and date handling | Passed (pre-existing) |
| `tests/test_activities.py` | Integration, state transitions | Activity status transitions | Passed (pre-existing) |
| `tests/test_routes.py` | Integration, config | Route registration, security headers, cookie config, protected routes | Passed (pre-existing) |
| `tests/test_core_journey.py` | End-to-end | Core farmer journey through the Flask client | Passed (pre-existing) |
| `tests/test_extended_flows.py` | End-to-end, smoke | All GET pages render; finance and report persistence | Passed (pre-existing) |
| `tests/test_risk.py` | Service | Risk scoring and unknown-state handling | Passed (pre-existing) |


## 3. New security tests in detail

| Test | Category | What it proves |
|---|---|---|
| `test_weather_api_does_not_leak_internal_exception_text` | Security, negative | A `RuntimeError` containing a filesystem path is **not** echoed to the client; a generic message is returned and HTTP 400 is preserved |
| `test_weather_api_still_surfaces_weather_error_wording` | Regression guard | `WeatherError` messages remain user-visible, so the fix did not over-redact legitimate validation text |
| `test_reverse_geocode_api_does_not_leak_internal_exception_text` | Security, negative | A connection exception containing an internal hostname is not echoed; returns 502 with a generic message |
| `test_reverse_geocode_api_rejects_out_of_bounds_coordinates` | Boundary | Latitude 91 is rejected with 400 and the documented message |
| `test_api_endpoints_require_authentication` | Authorization | All three JSON APIs redirect unauthenticated requests |
| `test_second_user_cannot_mutate_first_user_activity` | Cross-user isolation | A second authenticated user's POST leaves the owner's activity row `PENDING` |
| `test_intruder_dashboard_does_not_expose_other_farm_name` | Cross-user isolation | Another farmer's farm name never appears in the intruder's dashboard HTML |
| `test_password_change_invalidates_existing_sessions` | Session state | After a password change the old session is rejected and the new password works |
| `test_tampered_auth_token_is_rejected` | Session security | A forged `auth_token` in the cookie does not grant access |
| `test_protected_pages_do_not_render_tracebacks` | Error handling | An internal exception in the crop path yields 503 with no traceback and no internal path |
| `test_csrf_token_is_required_for_state_changing_posts` | CSRF | With `CSRF_ENABLED=True` a wrong token is rejected (400) and the forged record is never written, while the valid token succeeds |

## 4. Categories with no coverage yet

| Category | Status | Reason |
|---|---|---|
| Coverage measurement | NOT RUN | `coverage.py` is not installed in the environment |
| Accessibility automated audit | NOT RUN | No axe/Lighthouse integration present; accessibility changes are manual and reviewed by inspection only |
| Performance benchmarks | NOT RUN | No load-testing tool present. No latency numbers are claimed anywhere in this repository |
| Market live integration | BLOCKED | No successful live HTTP response has ever been observed |
| Disease classification | BLOCKED | No dataset or model exists |
| Farmer user study | NOT STARTED | Requires participants and ethics approval |

## 5. Browser automation

`scripts/browser_check.py` drives headless Microsoft Edge via Playwright against
a disposable SQLite database on port 5056. It registers a synthetic account,
performs manual farm setup, exercises the crop planner, lifecycle, activities,
report problem, password change and session behaviour, then measures responsive
layout at 1366 px, 768 px and 390 px. It records JavaScript errors, failed
requests and HTTP errors into `artifacts/browser_results.json`.

The script never touches the farmer database.

The actual result of the run performed in this work session is recorded in
`CLINE_PROGRESS.md` and in `docs/research/experimental_results.md`. Earlier
browser evidence in `docs/current_baseline.md` predates this session's changes
and is not current evidence for the present working tree.

## 6. Determinism notes

- All tests use `tmp_path` SQLite databases, so no test depends on or mutates
  `database.db`.
- External services are mocked with `monkeypatch`; no automated test calls
  Open-Meteo, Nominatim, BigDataCloud or data.gov.in.
- One incidental live Open-Meteo call was observed during a manual debugging
  step and is recorded as such in `docs/research/experimental_results.md`. It is
  not part of any test.
- No real credential appears in any test. All accounts are synthetic.
