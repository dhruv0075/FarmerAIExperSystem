# IEEE-style paper readiness assessment

**Status:** not publication-ready. This assessment describes repository
evidence and a path toward a defensible manuscript; it does not draft a
scientific contribution claim.

## What can be written now

### System/engineering paper material

The repository can support a careful technical description of:

- a Flask/Jinja and SQLite decision-support prototype;
- its authenticated workflows and the 23-table relational schema;
- the separation of crop-model inference from lifecycle and rule-based
  planning;
- a crop classifier training/evaluation pipeline using four scikit-learn
  candidates and a balanced 2,200-row/22-class local dataset;
- a stored crop-model benchmark result, clearly labeled as a development
  holdout whose score was used to select the winner;
- code-level disease screening with an existing MobileNetV3 Small checkpoint,
  while explicitly disclosing that training/evaluation provenance and
  performance are unknown;
- deterministic rules/calculations for lifecycle, activities, risk and
  explainable advisory generation; and
- software tests executed in a stated environment.

These support a systems description or prototype report, not evidence of
farmer benefit or deployed agronomic reliability.

### Empirical result that can be reported with qualifications

The checked-in crop benchmark result is Random Forest 0.9955 held-out
accuracy and 0.9955 macro F1 on the local 22-class dataset, after the training
pipeline compared four models. The held-out set was also used for selection.
The source provider/license/collection context are unresolved; split is random
and not geographic or temporal. Report the figure only as a **local
development benchmark**, not as test-set evidence from a fully independent
evaluation and not as field accuracy.

The current software-suite result (183 passed, one Windows joblib core-count
warning) is engineering verification. It is not a model-performance result.

## Claims that are not supported

Do not state or imply:

1. The crop classifier is accurate on farms, across India, or in a specified
   geography/season.
2. The disease classifier has known accuracy, detects all relevant diseases,
   is calibrated, or rejects unfamiliar images reliably.
3. The market adapter currently supplies complete/live nationwide data or
   that its forecast is predictively accurate.
4. The software improves yield, income, input efficiency, sustainability,
   decision quality, or farmer welfare.
5. Recommendations have been validated by farmers/agronomists, unless a
   verifiable protocol and results are added.
6. The system is novel compared to the broader field based on two papers.
7. All pages and dynamic content are fully translated into all three
   supported languages.
8. The deployment configurations prove a production service was provisioned,
   secure, durable or available.

## Minimum research work before a full paper

### Dataset and model evaluation

- Establish verifiable dataset publisher, version, license, collection
  geography/time, target definition and preprocessing.
- Freeze a training protocol before inspecting a final test set. Do not use the
  final holdout to select a model.
- Add independent temporal/geographic holdouts representing the intended
  population; document exclusion, duplicates and class support.
- Report per-class metrics and uncertainty, calibration and failure analysis;
  compare simple baselines and justify feature/label semantics.
- For disease screening, recover checkpoint lineage or train/reproduce from
  a documented dataset with image-level deduplication and separate
  train/calibration/held-out/real-world data. Measure the crop match policy,
  calibration and robustness to non-PlantVillage imagery. Do not use sample
  predictions as an accuracy proxy.
- For market forecasts, use verified, sufficiently long time series, prevent
  temporal leakage, compare naïve/seasonal baselines and report errors across
  commodities and markets. Establish data feed reliability separately from
  forecast quality.

### Product and human evaluation

- Define intended users, decisions, deployment region and safety boundaries.
- Obtain qualified agronomist review of configured ranges, rules, fertilizer
  reference entries and safety wording.
- If evaluating people, prepare a protocol, informed-consent/privacy plan,
  recruitment, evaluation measures and any required institutional ethics
  approval before collecting data.
- Measure outcomes against a baseline, not only usability or model metrics.
- Document offline behavior, stale-data handling, translation accuracy,
  accessibility and deployment reliability.

### Literature and reporting

- Run a reproducible systematic or scoping search: databases, exact search
  strings, date window, inclusion/exclusion rules, duplicate removal and
  screening counts.
- Verify every citation against publisher/Crossref/PubMed primary metadata;
  read full text before describing methods or limitations.
- Expand beyond the two currently reviewed crop-classification papers. Avoid
  claiming a field-wide gap from a narrow sample.
- State dataset license/provenance and software/model artifact versions.
- Follow applicable IEEE author and ethics requirements; do not invent
  authorship, affiliations, funding, ethics approval or conflicts of interest.

## Suggested manuscript structure

1. Abstract: prototype, precise study scope and bounded results only.
2. Introduction: cite verified context; avoid unsupported prevalence claims.
3. Related work: systematic evidence or an explicitly limited review.
4. System design: architecture, routes, dataflow and boundaries.
5. Data and methods: provenance, exact split/selection protocol and
   reproducibility.
6. Results: complete metrics and test status separated by evidence type.
7. Discussion: dataset shift, test reuse, model validity and operational
   constraints.
8. Limitations/threats to validity: prominent and specific.
9. Ethics, privacy, safety and deployment considerations.
10. Conclusion: engineering result; no unmeasured impact claim.

## Citation state

The current checked bibliography includes two crop-recommendation papers.
Crossref metadata for both and the accessible PMC abstract for Dey et al. were
checked in this audit. The Nature page for Shastri et al. returned HTTP 406,
so detailed paper claims were not independently verified; see
[RESEARCH_EVIDENCE_INVENTORY.md](RESEARCH_EVIDENCE_INVENTORY.md). A two-paper
reference list is not sufficient for a comprehensive IEEE related-work
section.

## Readiness verdict

| Dimension | Status |
|---|---|
| Prototype implementation description | **Ready to document, with source evidence** |
| Crop benchmark description | **Reportable only with protocol/provenance caveats** |
| Crop field/generalization claim | **Not ready; no external geographic/temporal validation** |
| Disease model performance | **Not ready; training lineage/evaluation unestablished** |
| Market forecast performance | **Not ready; usable live history not established** |
| Farmer impact or agronomic effectiveness | **Not ready; no field/user outcome study** |
| Novelty/literature gap claim | **Not ready; literature review is too narrow** |
| Full IEEE-style paper submission | **Not ready** |
