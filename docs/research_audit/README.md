# AgriWise AI research and engineering audit

**Audit date:** 2026-10-15
**Scope:** repository evidence in the current checkout; source, data and test
inspection; current full automated test run; bounded literature-source checks.
**Change boundary:** this audit and its follow-up update documentation only.
After the initial package was created, a follow-up pass corrected the
existing documentation conflicts listed in
[DOCUMENTATION_SOURCE_OF_TRUTH.md](DOCUMENTATION_SOURCE_OF_TRUTH.md).

## Executive assessment

AgriWise AI is a Flask/Jinja and SQLite decision-support prototype. The
repository contains one active crop-classification pipeline, rules and
heuristics for farm planning, external weather/geocoding adapters, and a
conditionally usable official-market-data adapter. Problem Report records
symptoms and optional reference photos without image inference. It is not a
field-validated autonomous agronomy system.

The crop model's recorded 0.9955 held-out accuracy and macro F1 are local
benchmark results on a balanced 2,200-row dataset whose provider, license,
geography and collection period are not established in this checkout. The
held-out split is also used to choose the winning model. These facts preclude
interpreting the figure as independent or field accuracy. Disease image
classification has been removed from the current application.

The current full test command completed with **164 passed, 1 environment
warning, 0 failures**. This is software-test evidence, not evidence that
recommendations improve farm outcomes. The warning is joblib's inability to
discover physical CPU cores on this Windows host; it falls back to logical
cores.

## Package contents

| File | Purpose |
|---|---|
| [PROJECT_INVENTORY.md](PROJECT_INVENTORY.md) | Application structure, request paths, feature map and SQLite entities. |
| [ML_AND_DATASET_AUDIT.md](ML_AND_DATASET_AUDIT.md) | Crop model, datasets, rules, metrics, provenance and limits. |
| [API_AND_DEPLOYMENT_AUDIT.md](API_AND_DEPLOYMENT_AUDIT.md) | API routes, third-party integrations, security and deployment constraints. |
| [TESTING_AUDIT.md](TESTING_AUDIT.md) | Current execution record, test inventory, coverage limits and older-test evidence. |
| [RESEARCH_EVIDENCE_INVENTORY.md](RESEARCH_EVIDENCE_INVENTORY.md) | Claim/evidence matrix, checked references and research gaps. |
| [DOCUMENTATION_SOURCE_OF_TRUTH.md](DOCUMENTATION_SOURCE_OF_TRUTH.md) | Evidence precedence and detected documentation drift. |
| [IEEE_PAPER_READINESS.md](IEEE_PAPER_READINESS.md) | What can be reported, what is not publication-ready, and required work. |

## Evidence conventions

- **Verified in source** means a current code path, data file, configuration or
  test was inspected. It does not mean the feature was field-validated.
- **Executed** means the command actually ran in this session and its result is
  recorded. Historical output in an existing document is not current execution.
- **Reported in repository** means the value appears in a checked-in artifact
  or document. Its generating run may not have been repeated during this
  source review.
- **Unverified / unknown** means evidence was absent, contradictory, or could
  not be established from the allowed sources. Similarity to a known public
  dataset is not provenance.
- **Not run** is distinct from failed, blocked, or passed.

## Reproduction notes

The test suite was run with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --no-header -p no:cacheprovider
```

Result: **164 passed, 1 warning, 0 failed**. The model-training
test passes temporary output paths and did not retrain the checked-in model.
However, importing `app.py` constructs its module-level Flask app and calls
database initialization. In this audit environment the configured path
resolved to the repository's `database.db`; the test run therefore invoked
initialization/migration logic against that path. Its records were not
inspected, and the pre-run file metadata was not captured, so whether existing
data/schema changed cannot be established. See
[TESTING_AUDIT.md](TESTING_AUDIT.md); do not claim the farmer database was
untouched.

The audit did not run model training, live API diagnostics, browser automation,
or deployment. Training overwrites model outputs; browser and diagnostic
scripts write artifacts and/or access external services. No credentials or
farmer record contents were inspected or copied into these documents.

## Bottom line

The implementation is suitable to describe as a working software prototype
with an experimentally evaluated crop classifier on a provenance-limited
benchmark. A research paper may accurately report system architecture,
software behavior and the recorded benchmark protocol/results with their
limitations. Claims of field accuracy, validated agronomic benefit, farmer
outcome improvement, operational market forecasts, novelty, or national
suitability are not supported by the evidence inspected here.
