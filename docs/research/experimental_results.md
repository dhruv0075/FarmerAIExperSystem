# Experimental results

Only results produced by an actual execution in this repository are recorded.
Commands are given so any reader can reproduce them. Nothing is inferred.

## E1 — Full automated test suite

Command:

```powershell
.venv\Scripts\python.exe -m pytest -q --no-header -p no:cacheprovider
```

Result: **145 passed, 1 warning, 0 failed** in 80.67 seconds.

The single warning is environmental, not an application defect:

```
tests/test_ml.py::test_training_creates_model_and_metrics
joblib/loky/backend/context.py:136: UserWarning: Could not find the number of
physical cores ... Returning the number of logical cores instead.
```

Baseline before this work session: **134 passed**. The delta is the 11 new
tests in `tests/test_security.py`. No pre-existing test was modified, weakened
or removed.

## E2 — Security regression suite (new)

Command:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_security.py -q --no-header -p no:cacheprovider
```

Result: **11 passed** in approximately 15 seconds.

These tests cover error-message disclosure, cross-user data isolation,
session invalidation on password change, forged session tokens, CSRF
enforcement, and absence of tracebacks in protected pages.

## E3 — Crop classifier evaluation

Source: `ml/model_metrics.json`, produced by `python ml/train_model.py`.

| Model | Held-out accuracy | Macro precision | Macro recall | Macro F1 | CV accuracy mean +/- std |
|---|---|---|---|---|---|
| Decision Tree | 0.9818 | 0.9830 | 0.9818 | 0.9817 | 0.9841 +/- 0.0073 |
| Random Forest | **0.9955** | 0.9957 | 0.9955 | **0.9955** | 0.9943 +/- 0.0051 |
| KNN | 0.9795 | 0.9804 | 0.9795 | 0.9793 | 0.9653 +/- 0.0121 |
| Gradient Boosting | 0.9886 | 0.9896 | 0.9886 | 0.9886 | 0.9926 +/- 0.0043 |

Protocol: stratified 80/20 split, `random_state=42`, 1760 train / 440 test.
Selection criterion: held-out macro F1. Selected: Random Forest.

**Interpretation limit.** These are local benchmark results on a dataset of
unresolved provenance with no geographic or temporal holdout. They are not
field accuracy and must not be reported as such.

## E4 — Live weather adapter (incidental observation)

During a debugging step, `GET /api/weather` for a farm at 18.5, 73.8 returned
HTTP 200 with a parsed Open-Meteo payload, `data_source` =
`CACHED LIVE WEATHER (Open-Meteo)`. This confirms the adapter reaches the
provider and parses a valid response in this environment.

This is a single incidental observation, not a controlled test, and it is
recorded as such. It does not establish reliability under timeout or outage;
those paths are covered by unit tests with mocks.

## E5 — Browser automation (headless Microsoft Edge via Playwright)

Command:

```powershell
.venv\Scripts\python.exe scripts\browser_check.py
```

Environment: Playwright 1.47.0 installed into `.venv`; Microsoft Edge present on
this machine. The script runs against a **disposable** SQLite database in a
temporary directory on port 5056 and never touches `database.db`.

Result: **exit code 0**, i.e. the script's own assertions all held.

| Check | Result |
|---|---|
| Landing page `/` | HTTP 200 |
| 3D field scene | `scene: "ready"`, `webgl_context_available: true` |
| `farm-setup-first-crop-planner` | 200 |
| 12 authenticated pages (dashboard, weather, daily-plan, seven-day-plan, crop-recommendation, activities, report-problem, market, history, research, lifecycle, settings) | all 200 |
| `sidebar-click-navigation` | 200 |
| `topbar-and-dashboard-cta-clicks` | 200 |
| `open-meteo-weather-api` | 200, `state: "available"` |
| `crop-weather-lifecycle-report-workflow` | 200 |
| `activity-create-complete-pending-workflow` | 200 |
| Responsive tablet 768 px and mobile 390 px layout bounds | assertions held |
| Mobile sidebar toggle and dashboard metric count | assertions held |
| Password change, re-login, logout and back-button session invalidation | assertions held |
| **JavaScript errors** | **0** |
| **HTTP errors (>=400)** | **0** |
| Failed browser requests | 1 — `bootstrap.bundle.min.js` from jsDelivr, `net::ERR_ABORTED` |

Artifacts written: `artifacts/browser_results.json`,
`artifacts/home_desktop.png`, `artifacts/mobile_dashboard.png`.

### Interpretation of the one failed request

The single failed request is the Bootstrap JS bundle on a CDN returning
`net::ERR_ABORTED`. This is a navigation-abort pattern (the document unloaded
while the script was in flight), not an application defect, and it did not
produce a JavaScript error or an HTTP error in the recorded run. It is reported
here rather than omitted because it was observed.

### Confirmed defect found and fixed by this run

The first execution of this script **failed** at line 72 with a Playwright
`TimeoutError` waiting for `[name=no_soil_test]`. That checkbox no longer exists
in `templates/farm_setup.html`: an earlier change made soil values required, and
`tests/test_black_box.py` explicitly asserts that `name="no_soil_test"` is
**absent** from the setup page.

So `scripts/browser_check.py` was stale relative to the current form contract.
It was updated to fill the four required soil fields with synthetic values
(N 90, P 42, K 43, pH 6.5). This is a test-harness defect, not an application
defect — the application was already correct and already covered by
`tests/test_black_box.py`.


## E6 — Experiments NOT run

| Experiment | Status | Reason |
|---|---|---|
| Geographic holdout | PENDING | No dataset with a geographic key and verifiable licence |
| Temporal holdout | PENDING | No timestamped dataset available |
| Near-duplicate leakage analysis | PENDING | Not implemented in this session |
| Class-pooling ablation (agricultural vs horticultural separately) | PENDING | Requires per-crop yield labels not present |
| Live market API success | BLOCKED | No successful HTTP response has ever been observed |
| Price forecast error | PENDING | Requires 20+ verified historical observations |
| Disease classification | BLOCKED | No dataset or model exists |
| Farmer user study | NOT STARTED | Requires participants and ethics approval |
| Browser automation run | **DONE** | Executed successfully; see E5 |
| Coverage measurement | BLOCKED | `coverage.py` not installed |

No accuracy figure, significance test, comparison or field result has been
invented to fill any row above.
