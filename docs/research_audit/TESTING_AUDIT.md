# Testing audit

**Executed:** 2026-10-15, repository venv Python 3.12.4 on Windows.
**Scope:** current automated pytest suite only. No coverage, browser suite,
live API check, model training run or deployment check was performed.

## Current full suite

Repository-relative equivalent of the invoked repository-venv command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --no-header -p no:cacheprovider
```

Observed output:

```text
164 passed, 1 warning
```

There were **0 failures**. The warning came from
`joblib.externals.loky.backend.context`: Windows returned `WinError 2` when
joblib tried to discover physical CPU cores, so joblib used the logical-core
count. This was not a test failure or an application assertion.

The model test's training case passes explicit temporary model/metrics paths;
no training command was invoked and no checked-in model artifact was trained
by this run. Many test-created application instances use disposable SQLite
databases. **Important side-effect qualification:** importing `app.py`
executes the module-level `app = create_app()`, and `create_app()` calls
`db_init(app.config["DATABASE"])`. The configured database path in this
environment resolved to the repository's `database.db`. The file's
post-run last-write metadata was observed as
`2026-10-15T17:18:47.8256897+05:30`. Because no pre-run metadata was recorded
and database contents were deliberately not inspected, this audit cannot
establish whether the test import initialized or migrated existing schema/data.
The migration code can assign auth tokens to legacy users with missing tokens;
whether that branch applied is unknown because no records were inspected.
Therefore it would be inaccurate to claim the full suite never touched the
configured farmer database. Do not rerun without first isolating the app's
data directory in the environment **before Python imports `app`** and
confirming that the tests use that isolated path.

The live market and weather service behaviors are exercised with mocked data
in focused tests; the full suite itself is not a live integration result.

## Test modules present

| Module | Primary concern |
|---|---|
| `tests/test_activities.py` | Activity lifecycle, status, linking and state behavior. |
| `tests/test_black_box.py` | User-input partitions, validation, registration and workflow behavior. |
| `tests/test_core_journey.py` | Farm journey integration using temporary data and controlled weather. |
| `tests/test_disease_detection.py` | Confirms the removed image-screening URL is not registered, Problem Report retains photos as private references, and crop recommendation uses the original dataset. |
| `tests/test_extended_flows.py` | Page renders and finance/report flows. |
| `tests/test_i18n.py` | Locale selection/persistence, invalid language handling, fallback and selected route strings. |
| `tests/test_integrity.py` | Form/database field consistency, upload and ownership/integrity cases. |
| `tests/test_lifecycle.py` | Crop stage calculations and dates. |
| `tests/test_market_integration.py` | Market adapter parsing/cache/failure cases with fixtures/mocks. |
| `tests/test_ml.py` | Crop training function using temp outputs and prediction interface. |
| `tests/test_reliability_repairs.py` | Input/API error contracts, market history and financial validations. |
| `tests/test_risk.py` | Risk computation and unknown/missing context behavior. |
| `tests/test_routes.py` | Route smoke, authentication and security headers/session config. |
| `tests/test_rules.py` | Expert-system rules and conflict behavior. |
| `tests/test_security.py` | Error disclosure, user isolation, session, token and CSRF regressions. |
| `tests/test_weather.py` | Weather parsing, timeouts, cache and stale fallback. |

`tests/conftest.py` adds the project root to `sys.path`. The test count is
from actual pytest execution, not the number of test cases inferred by
inspection.

## What the tests establish

- Flask route and service behavior for covered inputs, using the test
  configuration and temporary databases.
- Regression expectations for selected authentication, CSRF, ownership,
  image-validation and error-handling cases.
- Crop-model training code can run on a small synthetic dataset when explicit
  temporary output paths are supplied; inference return contract can be
  exercised with the checked-in model in the configured test environment.
- Problem-report tests cover photo handling, report storage, and the original
  crop-recommendation dataset path.
- Localization is tested on selected routes and translation failure/invalid
  selection cases. It does not prove every phrase and dynamic message across
  every page is translated.
- Provider error/parse/fallback logic is covered using controlled fixtures or
  mocks. It does not prove external uptime, credentials, completeness or
  current live values.

## Not run / not established

| Activity | Status | Reason / effect |
|---|---|---|
| Coverage measurement | NOT RUN | No coverage report was generated in this audit. |
| Browser visual/responsive automation | NOT RUN | Existing browser script writes artifacts and starts an application; the current audit was constrained to documentation-only changes and did not create new artifacts. Earlier browser runs are historical and predate the latest homepage redesign. |
| Live weather, geocoding, market requests | NOT RUN | Automated tests mock provider behavior; no current external transaction is needed for a source audit. |
| Crop model retraining | NOT RUN | Would overwrite checked-in model/evaluation artifacts. |
| Load/performance testing | NOT RUN | No performance benchmark or current latency result was produced. |
| Accessibility audit | NOT RUN | No automated axe/Lighthouse run was performed in this audit. |
| Field or user study | NOT STARTED | Requires participants, protocol and appropriate ethics/consent review. |
| Deployment smoke test | NOT RUN | No hosting environment was provisioned or contacted. |

## Historical-test documentation drift

`docs/test_inventory.md`, `docs/research/experimental_results.md` and
`README.md` contain earlier results such as **145 passed** and a prior
browser run. This audit's current full run is **164 passed**. Cite the
execution record above for this date; do not present the historical run as
current.

The older browser report also describes a 3D home scene as ready. The current
worktree's prior homepage redesign removed the home hero's external image/3D
scene, and this audit did not repeat browser automation. Therefore the old
browser evidence does not verify the current homepage UI.

## Reproducibility

Re-run the command above from the repository root using the same environment.
For precise comparison, record Python and dependency versions, OS, exact
command and stdout. Avoid `python ml/train_model.py` when preserving current
model artifacts; that command writes the checked-in model, metrics and
confusion matrix.
