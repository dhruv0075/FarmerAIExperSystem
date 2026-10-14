# Research paper outline

Sections are populated only where this repository provides evidence. Sections
that would require experiments or citations we do not have are marked
**PENDING** rather than filled with plausible-sounding text.

---

## 1. Abstract — DRAFT

AgriWise AI is a Flask and SQLite decision-support system that combines a
trained crop classifier with crop-lifecycle planning, weather-aware advisory
rules, official market-price retrieval, financial tracking and guided crop
problem reporting. This paper describes the system architecture, the
evaluation of the crop classifier, and the integration of multiple
information sources behind a single farm-state model.

The classifier reaches 0.9955 held-out accuracy and 0.9955 macro F1 on a
2200-row, 22-class dataset, selected from four candidates by held-out macro F1
with 5-fold stratified cross-validation.

**Explicit limitation to state in the abstract:** the training dataset's
provenance, licence, collection geography and collection period are not
established, and no geographic or temporal holdout was performed. The reported
metrics are therefore local benchmark results and are not evidence of field
accuracy.

**PENDING:** no farmer field trial, user study, or outcome measurement exists.
Any abstract sentence implying agronomic benefit would be unsupported.

## 2. Introduction — DRAFT

Frame the problem as fragmentation: crop selection, lifecycle execution,
weather response and market timing are usually separate decisions supported by
separate tools. Introduce the system as an integration effort.

**PENDING:** a citation-backed statement of the scale of fragmentation.

## 3. Problem statement — DRAFT

State the concrete engineering problem: how to keep one coherent, owned,
persisted farm state across heterogeneous data sources with differing
availability, while never presenting stale, fabricated or unavailable data as
if it were current and reliable.

## 4. Related work — DRAFT

Use `literature_review.md`. Two verified peer-reviewed sources are available:

- L1: Shastri, Kumar, Mansotra & Salgotra (2025), *Scientific Reports* 15:25498, DOI 10.1038/s41598-025-07003-8
- L2: Dey, Ferdous & Ahmed (2024), *Heliyon* 10(3):e25112, DOI 10.1016/j.heliyon.2024.e25112

**PENDING:** a systematic search with documented query strings and inclusion
criteria. Two papers do not constitute a related-work section.

## 5. Research gap — DRAFT

Use `research_gap_evidence.md`. Only G1 and G2 are supported by the reviewed
papers. G4 and G5 are **not** established.


## 6. Objectives and contributions — DRAFT

Distinguish carefully, because conflating these is the main scientific risk in
this project:

1. **Existing techniques reused.** Supervised classification, stratified
   cross-validation, rule-based advisory, HTTP caching with TTL and stale
   fallback.
2. **Engineering integration (the actual contribution).** A single persisted
   `FarmState` that joins soil, cycle, weather, activities, disease reports,
   expenses and sales, with per-user ownership enforced at every route, and
   with explicit data-freshness labelling for each external source.
3. **Software features implemented.** Lifecycle stage generation, activity
   completion/skip/reschedule, deterministic financial calculations, market
   comparison and sell planning, guided symptom reporting.
4. **Empirical findings supported by experiments.** The classifier comparison
   in `methodology.md`, and the deterministic financial and validation tests.
5. **Potential future contribution (unvalidated).** Whether joining
   recommendation, lifecycle, weather and market data with explicit
   uncertainty improves farmer decisions. **Untested.**

**Do not claim novelty** for items 1–3. A collection of existing features is
not automatically a novel research contribution.

## 7. System architecture — DRAFT

Describe the existing layered architecture: Jinja templates and static assets;
Flask routes with `login_required` and CSRF enforcement; a service layer under
`services/`; SQLite with foreign keys and per-user ownership scoping; a
separate ML service; and external adapters for weather, geocoding and official
market data, each with explicit timeout and fallback behaviour.

## 8. Dataset and methodology — DRAFT

Use `dataset_provenance.md` and `methodology.md`. State provenance as
unresolved. Do not omit this to make the results look stronger.

## 9. Experimental design — DRAFT

Use `methodology.md`. Include the seed (`random_state=42`), the split ratio,
the CV configuration, the metrics, and the software versions.

## 10. Results — DRAFT

Report the four-model table exactly as recorded. Include per-class metrics from
`ml/model_metrics.json`. Report the test count for the software evaluation.

**PENDING:** geographic or temporal holdout results; any market forecast error
metric; any disease classification metric.

## 11. Discussion — DRAFT

Discuss the >0.99 accuracy as a symptom of near-separable classes under the
given sampling rather than proof of field performance. Cross-reference L1
(similar magnitude) and L2 (explicit recommendation against class pooling).

## 12. Limitations and threats to validity — DRAFT

Use `limitations_and_future_work.md`. This section must be prominent, not
buried.

## 13. Conclusion and future work — DRAFT

State the engineering contribution and the bounded empirical result. State
plainly that no field validation has been performed.

## 14. References

1. Shastri S., Kumar S., Mansotra V., Salgotra R. Advancing crop recommendation system with supervised machine learning and explainable artificial intelligence. *Scientific Reports*. 2025;15:25498. DOI 10.1038/s41598-025-07003-8
2. Dey B., Ferdous J., Ahmed R. Machine learning based recommendation of agricultural and horticultural crop farming in India under the regime of NPK, soil pH and three climatic variables. *Heliyon*. 2024;10(3):e25112. DOI 10.1016/j.heliyon.2024.e25112

**PENDING:** substantially more references, verified individually.

---

## Publication readiness

**This outline is NOT publication-ready.** Missing: systematic literature
search, geographic or temporal validation, a verified dataset citation, a
field or user study, and market forecast evaluation.
