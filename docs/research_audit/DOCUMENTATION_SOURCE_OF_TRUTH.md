# Documentation and source-of-truth map

**Purpose:** direct future dossier edits to evidence that can establish the
claim, and flag conflicting historical prose. This file adds an audit map; it
does not edit or supersede existing project documents.

## Evidence precedence

When sources disagree, prefer these sources in order:

1. **Current executable code and current tests** for actual implemented
   behavior and tested contracts.
2. **Current raw data/artifact metadata** for contents and derived results;
   artifact values do not prove their provenance.
3. **Reproduced command output** for current execution claims.
4. **External primary source/registry** for external bibliographic or API
   facts.
5. **Existing project documentation** as explanatory history; documents can
   be stale, inconsistent, or more confident than current evidence.

Tests establish only the inputs, route/path and assertions that they execute.
An existing implementation or passing test is not field validation.

## Repository source-of-truth map

| Claim area | Preferred repository source |
|---|---|
| Flask routes, auth checks and app lifecycle | [`app.py`](../../app.py), route function and decorators. |
| Database tables and migrations | [`db.py`](../../db.py), especially DDL and `_apply_migrations`. |
| Crop training algorithm | [`ml/train_model.py`](../../ml/train_model.py) and [`services/crop_ml_service.py`](../../services/crop_ml_service.py). |
| Crop runtime prediction | [`services/crop_service.py`](../../services/crop_service.py) and `/crop-recommendation` route in `app.py`. |
| Crop dataset contents | [`data/Crop_recommendation.csv`](../../data/Crop_recommendation.csv); for safe aggregate inspection, use row/column/class counts rather than copying personal data (the dataset is not farmer-identifiable in the current audit). |
| Crop metric values | [`ml/model_metrics.json`](../../ml/model_metrics.json); confirm protocol from active training implementation. |
| Disease inference | [`agriwise_disease_model/disease_predictor.py`](../../agriwise_disease_model/disease_predictor.py), class map and [`services/disease_service.py`](../../services/disease_service.py). |
| Disease workflow separation | `/disease-detection` and `/report-problem` in [`app.py`](../../app.py); tests in [`test_disease_detection.py`](../../tests/test_disease_detection.py). |
| Weather and location adapters | [`weather_service.py`](../../services/weather_service.py), [`location_service.py`](../../services/location_service.py). |
| Official market adapter and forecast | [`official_market_service.py`](../../services/official_market_service.py), [`market_forecast_service.py`](../../services/market_forecast_service.py). |
| Translations | [`i18n_service.py`](../../services/i18n_service.py), `locales/*.json`, templates and [`test_i18n.py`](../../tests/test_i18n.py). Code architecture is not a translation-completeness metric. |
| Deployment intent | [`render.yaml`](../../render.yaml) and [`docs/vercel.md`](../vercel.md); neither proves provisioning or successful deployment. |
| Test result for this audit | Exact command/output in [TESTING_AUDIT.md](TESTING_AUDIT.md), executed 2026-10-15. |
| Research citations | DOI registry and accessible publisher/archive sources listed in [RESEARCH_EVIDENCE_INVENTORY.md](RESEARCH_EVIDENCE_INVENTORY.md). |

## Existing-document drift and contradictions found

This table records material drift found during the audit and the current
resolution status. Existing documentation was selectively corrected after
the audit review; the table preserves the evidence trail and notes remaining
historical limits.

| Existing documents | Conflict / caveat | Audit treatment |
|---|---|---|
| [`docs/test_inventory.md`](../test_inventory.md), [`docs/research/experimental_results.md`](../research/experimental_results.md), [`README.md`](../../README.md) | They contained earlier full-suite counts and prior browser evidence. Current 2026-10-15 run reports 183 passed and one warning. | Updated documents distinguish historical from current results. The current test-run database side effect remains explicitly unresolved; see [TESTING_AUDIT.md](TESTING_AUDIT.md). |
| [`docs/data_provenance.md`](../data_provenance.md), [`docs/research/experimental_results.md`](../research/experimental_results.md), [`docs/model_cards.md`](../model_cards.md) | Older prose said no disease model/checkpoint existed, while the current tree contains checkpoint, class mapping, predictor and tests. | Updated: inference artifact is present; training lineage and performance remain unknown/unmeasured. |
| [`docs/api_integrations.md`](../api_integrations.md), [`README.md`](../../README.md), [`docs/engineering_report.md`](../engineering_report.md) | Historical diagnostic records conflict about whether the market API reached TLS; neither records usable HTTP price data. | Updated to preserve both historical observations and report current live status as unverified; no new network diagnostic was run. |
| [`docs/research/experimental_results.md`](../research/experimental_results.md) vs. current homepage worktree | Historical browser result records the old 3D scene as ready. The existing uncommitted homepage work removes that homepage 3D/remote-image hero; no current browser rerun was performed. | Historical result is not evidence for the current homepage. |
| [`docs/database_schema.md`](../database_schema.md) vs. current DDL | The summary is a snapshot and does not enumerate all currently created entities/columns and migrations. | Use current `db.py` for present schema; this audit counts 23 `CREATE TABLE IF NOT EXISTS` statements. |
| [`docs/research/literature_review.md`](../research/literature_review.md) | The older R2 summary omitted the abstract's XGBoost best-model statement and crop-category recommendation. Details for R1 were not fully rechecked. | Updated R2 wording from the accessible PMC abstract. R1's detailed claims remain not independently verified in this audit. |
| [`docs/requirements_audit.md`](../requirements_audit.md), [`docs/engineering_report.md`](../engineering_report.md), [`docs/database_schema.md`](../database_schema.md) | Older docs contained a 24-table count; current DDL has 23 create-table statements. The schema overview is a snapshot. | Updated the count where it appeared as a current assertion; use `db.py` for complete current DDL. |
| [`docs/feature_audit_v2.md`](../feature_audit_v2.md) | The dated UI audit called disease AI unavailable, gave an old test baseline, and described the previous homepage and a single market diagnostic result as current. | Added a clear historical-snapshot note and corrected those status descriptions; no browser test was run during the doc update. |

## Practical documentation rule

For each future claim, record (a) exact source file/function or external
reference, (b) whether it was executed or only inspected, (c) date/environment
for results, and (d) limitations. Avoid ambiguous words such as “AI-powered,”
“accurate,” “verified,” “real-time,” “national,” “safe” or “personalized”
unless the evidence directly supports the precise meaning.
