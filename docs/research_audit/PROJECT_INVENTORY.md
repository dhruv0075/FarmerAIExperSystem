# Project inventory

**Basis:** current repository source and selected tests, inspected 2026-10-15.
This is a source-level inventory, not a production availability or user-study
report.

## System at a glance

| Layer | Current implementation | Evidence |
|---|---|---|
| Web entry point | Flask application factory and module-level app in `app.py`; routes render Jinja templates and expose selected JSON endpoints. | [`create_app`](../../app.py#L302), route definitions in [`app.py`](../../app.py#L385). |
| Frontend | Jinja templates, CSS, JavaScript, Bootstrap and charts/maps where used. | [`templates/`](../../templates), [`static/`](../../static). |
| Localization | Shared `t` and `td` template helpers backed by UTF-8 JSON resources for English (`en`), Marathi (`mr`), Hindi (`hi`); selected locale is kept in Flask session. | [`i18n_service.py`](../../services/i18n_service.py), [`locales/`](../../locales), [`set_language`](../../app.py#L390), [`base.html`](../../templates/base.html). |
| Application logic | 23 service modules cover crop classification/explanations, decisions, weather, risk, lifecycle, activities, disease screening, market, reports, resources, finances, fertilizer, notifications and location. | [`services/`](../../services). |
| Persistence | SQLite database initialized on application startup with foreign keys and compatibility migrations. | [`init_db`](../../db.py#L23), [`_apply_migrations`](../../db.py#L520). |
| Model artifacts | Crop classifier pickle, crop metrics, confusion matrix, and disease checkpoint/class mapping are present in the repository. | [`ml/`](../../ml), [`agriwise_disease_model/`](../../agriwise_disease_model). |
| Tests | 18 test modules, including routes, core journey, model, disease, weather, market, i18n, integrity and security-oriented cases. | [`tests/`](../../tests); current execution in [TESTING_AUDIT.md](TESTING_AUDIT.md). |

## Product workflows and actual paths

The following table distinguishes implemented request paths from claims that
require external data or empirical validation.

| Workflow | Entry point and implementation | Observed scope / limitation |
|---|---|---|
| Public landing/about | `/`, `/about`; `index` and `about` render Jinja templates. | Public informational pages. Current homepage visual change is pre-existing worktree content; this audit does not modify it. |
| Authentication and farm setup | `/register`, `/login`, `/logout`, `/farm/setup`, `/farm`; uses Werkzeug password hashes, session user ID plus DB auth token, and farm-owned records. | Registration/login and session flows are covered by route/security tests; see [API_AND_DEPLOYMENT_AUDIT.md](API_AND_DEPLOYMENT_AUDIT.md). |
| Dashboard and plans | `/dashboard`, `/daily-plan`, `/seven-day-plan`; assembles farm state and calls risk, rules, lifecycle and orchestration services. | A decision-support composition; not a proof of crop outcome or agronomic efficacy. |
| Crop recommendation | `/crop-recommendation`, `/api/recommend-crop`; validates seven numeric soil/climate inputs, loads saved crop model, stores inputs/result, and shows an explanation. | The route calls `services.crop_service.predict_crop`; the active training command is `ml/train_model.py` and `services.crop_ml_service`. See [ML_AND_DATASET_AUDIT.md](ML_AND_DATASET_AUDIT.md). |
| Lifecycle and activities | `/lifecycle`, `/activities`, activity create/status routes; profile durations, stage calculations and rule/template-based tasks. | Calendar/stage heuristics are configured in code. Suggested tasks remain distinct from farmer-confirmed completion. |
| Expert system/advisories | `/expert-system`, `/advisories`, `/advisories/generate`; explicit rules over supplied weather, soil, crop stage and confirmed activity history. | Deterministic IF/THEN logic, not a trained model. Knowledge validity and local applicability are not independently established. |
| Disease image screen | `/disease-detection`; validates the submitted image and calls `screen_crop_image`. | Uses the optional 38-class checkpoint where dependencies/artifact load; only returns an unverified same-crop suggestion. Unsupported/mismatched classes are suppressed. No disease evaluation score is established. |
| Symptom problem report | `/report-problem`, `/disease-result/<id>`, `/disease-image/<id>`; records symptoms and optional private photo. | Separate from standalone Disease Detection. Report submission does not itself constitute a diagnosis. |
| Weather/location | `/weather`, `/api/weather`, `/api/location`, `/api/reverse-geocode`; calls external forecast/geocoder adapters. | Modeled weather, not a farm sensor. External service success varies by network and provider. |
| Market/sell planner | `/market`, `/market/refresh`, `/sell-planner`; official adapter and optional price-history regression. | Live usable records are unverified; the adapter limits individual fetches to a 10-record sample. Forecasts may be unavailable. |
| Profit/finance | `/profit-planner`, `/expenses`, `/add-sale`, activity-linked expense flow; calculation services and user-recorded transactions. | Projections are not verified offers, yields or financial outcomes. |
| Other decision support | `/fertilizer`, `/resources`, `/what-if`, `/compare-crops`, `/risk-analysis`, `/ml-analytics`, `/history`, `/report`, `/research`. | A mix of fixed reference values, rules, calculations and persisted farmer data. Do not treat each page as a trained/validated AI subsystem. |
| Account and supporting pages | `/notifications`, `/settings`, `/data-transparency`, `/about`; pages are individually routed. | Localization is shared, but complete translation coverage of every user-entered/dynamic or hard-coded phrase has not been measured. |

The route list can be cross-checked against decorators in [`app.py`](../../app.py#L385).
Routes requiring a login use `login_required`; `/healthz` and several
informational pages are public. JSON API protection is detailed in the API
audit.

## Persistence model

`db.py` currently creates 23 tables. These are operational entities, not
training sets:

1. `users`
2. `farms`
3. `soil_records`
4. `crop_recommendations`
5. `crop_cycles`
6. `crop_stages`
7. `weather_records`
8. `market_prices`
9. `market_forecasts`
10. `mandis`
11. `advisories`
12. `notifications`
13. `farm_activities`
14. `disease_reports`
15. `disease_predictions`
16. `fertilizer_recommendations`
17. `resources`
18. `resource_prices`
19. `farm_expenses`
20. `sales`
21. `what_if_runs`
22. `risk_snapshots`
23. `recommendation_feedback`

The source has 23 `CREATE TABLE IF NOT EXISTS` statements. Schema definitions
and migrations are in [`db.py`](../../db.py); the older schema summary in
[`docs/database_schema.md`](../database_schema.md) is not a complete
replacement for current DDL.

## Shared state and ownership

`load_farm_state_object` assembles the authenticated farmer, farm, soil, crop
cycle, weather, activity, disease-report and finance records; the
`FarmState`/daily-plan orchestration layer consumes these records. Relevant
source: [`load_farm_state_object`](../../app.py#L237),
[`FarmState`](../../services/decision_orchestrator.py#L12).

Farm and record ownership must still be assessed route by route; existence of
foreign keys alone does not prove authorization. Security-oriented regression
tests cover selected cross-user cases, but this is not a complete access
control audit.

## Localization scope

The locale helper validates supported language codes and falls back to English
for missing translation values. The language route persists the selection in
session. Current test coverage verifies language persistence/invalid values,
missing-key fallback and selected screens in all three languages. It does not
establish that every template phrase, dynamic stored advisory, third-party
content or all modules are completely translated.

Do not describe the entire application as fully multilingual without a
template-by-template and dynamic-content coverage audit. The shared resource
architecture is reusable; coverage is a separate property from architecture.

## Worktree preservation note

When this audit was prepared, the worktree already contained eight modified
files from the preceding typography/homepage task:

- `static/css/product.css`
- `templates/about.html`
- `templates/advisories.html`
- `templates/base.html`
- `templates/error.html`
- `templates/farm_profile.html`
- `templates/history.html`
- `templates/index.html`

They are unrelated pre-existing changes and are not part of this audit. This
package does not revert or edit them.
