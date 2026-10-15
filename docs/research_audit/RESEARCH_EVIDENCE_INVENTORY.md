# Research claim and evidence inventory

**Purpose:** provide a conservative ledger of statements that could appear in
a dossier or paper. “Verified” is scoped to the stated source and does not
mean scientifically validated in the field.

## Claim matrix

| Claim | Evidence in this checkout | Status / permissible wording |
|---|---|---|
| The project integrates crop recommendation, lifecycle, farm activities, weather-aware rules, market display and record-keeping in one Flask app. | Routes in [`app.py`](../../app.py); services under [`services/`](../../services); SQLite schema in [`db.py`](../../db.py). | **Verified as software structure.** Say that these workflows are implemented in this prototype, not that they improve decisions/outcomes. |
| Crop classifier uses seven soil/climate features and predicts one of 22 classes. | Dataset schema and [`crop_ml_service.py`](../../services/crop_ml_service.py); model card; `ml/model_metrics.json`. | **Verified in repository.** |
| Crop held-out accuracy and macro F1 are 0.9955 for Random Forest. | Checked-in metrics JSON and training code. | **Reported benchmark**, not reproduced in this audit; selected using the same held-out split; dataset provenance unresolved. State all qualifications. |
| Crop dataset is a representative national agricultural dataset. | No collection source, geography, license or dates established. | **Unsupported. Do not claim.** |
| Weather forecasts are measured on the farm. | Open-Meteo forecast fields and docs. No sensor data path established. | **False for current source.** Describe as modeled provider weather, not sensor observation. |
| Market prices are live, complete, nationwide or operationally validated. | data.gov.in adapter limits fetch to 10 records; prior diagnostic timed out at HTTP-response stage after DNS/TCP/TLS. | **Unverified.** Distinguish configured code from verified provider records. |
| Market forecast accuracy is known. | Regression computes MAE/RMSE only when a single market/variety has at least 20 distinct daily rows; no live history-backed result established. | **Not established.** Do not publish a forecast-quality claim. |
| Risk, suitability, lifecycle and fertilizer scores are learned from data. | Service implementations use thresholds, weights, configured tables and explicit rules. | **Not supported.** Describe as deterministic/heuristic logic. |
| The product has been validated with farmers or improves yield/profit. | No trial or user-study records found. | **Unsupported.** No outcome claim. |
| Full app is translated into English, Marathi and Hindi. | Locale resources, shared helpers and selected-route tests exist; all pages/dynamic text not audited end-to-end. | **Partial/coverage unknown.** State language support architecture and tested screens only. |
| Current application tests pass. | Full pytest run 2026-10-15, exact command and output in [TESTING_AUDIT.md](TESTING_AUDIT.md). | **Verified for that run/environment:** 183 passed, one environment warning. Not equivalent to production assurance. |

## Literature-source checks

Literature verification was deliberately narrow. Metadata and accessible
abstracts are not a systematic review.

### R1 — crop recommendation / explainability

Crossref registry metadata verified title, authors, DOI, journal title,
volume and publication date:

> S. Shastri, S. Kumar, V. Mansotra, and R. Salgotra, “Advancing crop
> recommendation system with supervised machine learning and explainable
> artificial intelligence,” *Scientific Reports*, vol. 15, Art. no. 25498,
> 2025, doi: 10.1038/s41598-025-07003-8.

Registry source: [Crossref DOI record](https://api.crossref.org/works/10.1038/s41598-025-07003-8).
The Nature publisher page returned HTTP 406 to the retrieval tool during this
audit. Accordingly, the bibliographic record is checked, but claims about the
paper's detailed methodology, exact metrics, geographic/temporal evaluation
or limitations are **not independently verified here**. Existing
[`docs/research/literature_review.md`](../research/literature_review.md)
contains such claims; do not promote those details to verified evidence based
on this audit alone.

### R2 — agricultural/horticultural crop recommendation

Crossref metadata and the accessible PubMed Central record verified:

> B. Dey, J. Ferdous, and R. Ahmed, “Machine learning based recommendation of
> agricultural and horticultural crop farming in India under the regime of
> NPK, soil pH and three climatic variables,” *Heliyon*, vol. 10, no. 3,
> Art. no. e25112, 2024, doi: 10.1016/j.heliyon.2024.e25112.

Sources: [Crossref DOI record](https://api.crossref.org/works/10.1016%2Fj.heliyon.2024.e25112)
and [PubMed Central full text / abstract](https://pmc.ncbi.nlm.nih.gov/articles/PMC10844259/).
The abstract describes Kaggle-sourced data with NPK, soil pH, temperature,
rainfall and humidity; evaluates models over agricultural, horticultural and
combined crop datasets; and says results strongly suggest evaluating
categories separately rather than combining them. It reports XGBoost as the
highest-accuracy method in that study. These are that paper's claims, not
results reproduced in AgriWise AI.

The fact that one paper reports a category-pooling result does not by itself
establish a universal rule for all crops, datasets or deployment regions. The
review sample here is two records, not a systematic literature search.

## Research gaps and limits

The repository's [`research_gap_evidence.md`](../research/research_gap_evidence.md)
is appropriately cautious about a narrow literature base. This audit further
classifies the evidence:

- **Researchable threat to validity:** no geographic/temporal holdout for the
  local crop classifier and unresolved dataset provenance.
- **Operational evidence gap:** no current successful official market-data
  record sample established.
- **Review limitation:** two papers cannot support claims about prevalence
  across the entire crop-recommendation or precision-agriculture field.
- **Evaluation gap:** no user study, field trial or farmer outcome measure.

No claim of novelty or research contribution is made by this evidence ledger.
Integration of existing techniques may be described as an engineering
artifact; a scientific novelty claim requires broader systematic review and
comparative evidence.

## Search/retrieval record

On 2026-10-15, the audit used DOI-resolving Crossref records for R1/R2 and
PubMed Central for R2. Nature blocked the direct page with HTTP 406; PubMed
page access was also blocked by a cookie requirement, while PMC was
accessible. No search query, inclusion criteria or screening protocol for a
systematic review was run. URLs and exact retrieval limitations are retained
here to make the evidence boundary explicit.
