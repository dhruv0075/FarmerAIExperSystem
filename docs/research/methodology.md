# Methodology and reproducible evaluation

This document describes what was actually executed, with exact commands. It
does not describe experiments that were not run.

## Research question (current, evidence-bounded)

> How can crop recommendations and crop-lifecycle decision support be combined
> with weather and market information while explicitly communicating
> uncertainty and data limitations?

Status: **framing, not a validated contribution.** The question is supported by
the features implemented in this repository. It is not established as novel
against the literature; see `research_gap_evidence.md`.

## Dataset

- File: `data/Crop_recommendation.csv`
- 2200 rows, 22 classes, exactly 100 rows per class.
- Features (in model order): `N`, `P`, `K`, `temperature`, `humidity`, `ph`, `rainfall`.
- Target: `label`.
- Measured quality: 0 null feature values, 0 exact duplicate rows, all values finite and range-checked.
- **Provenance: unresolved.** Provider, licence, collection geography, collection period and field representativeness are not established by the repository. See `dataset_provenance.md`.

## Evaluation protocol (as implemented in `ml/train_model.py`)

1. Load and validate the dataset; reject non-finite or out-of-range rows.
2. Stratified 80/20 train/test split with `random_state=42`.
3. Train four candidates: Decision Tree, Random Forest, scaled KNN,
   Histogram Gradient Boosting.
4. Run 5-fold stratified cross-validation on the training split.
5. Select the best model by held-out macro F1.
6. Persist the best model to `ml/crop_model.pkl` and all metrics to
   `ml/model_metrics.json`.

### Reproducing it

```powershell
python ml/train_model.py
```

## Recorded results (from `ml/model_metrics.json`)

| Model | Held-out accuracy | Macro F1 | CV accuracy (mean +/- std) |
|---|---|---|---|
| Decision Tree | 0.9818 | 0.9817 | 0.9841 +/- 0.0073 |
| Random Forest | **0.9955** | **0.9955** | 0.9943 +/- 0.0051 |
| KNN | 0.9795 | 0.9793 | 0.9653 +/- 0.0121 |
| Gradient Boosting | 0.9886 | 0.9886 | 0.9926 +/- 0.0043 |

Selected model: Random Forest. Held-out test set: 440 samples.

## Threats to validity (stated, not resolved)

1. **No geographic holdout.** Rows are split at random, so rows from the same
   region, season or collection batch can appear in both train and test. This
   inflates the estimate for any spatially structured dataset.
2. **No temporal holdout.** The same argument applies to time.
3. **Possible near-duplicate rows.** Zero *exact* duplicates were found, but
   near-duplicates across the N/P/K/climate space were not measured. In a
   perfectly balanced 100-per-class dataset, near-duplicates are plausible and
   would leak information.
4. **Class pooling.** 22 agronomically heterogeneous classes share one
   classifier. L2 (`literature_review.md`) explicitly recommends against this.
5. **Unverified provenance.** Without collection geography and protocol, the
   test set is not a sample of any known population.
6. **No field validation.** No accuracy figure here predicts performance on a
   real farm.

## Software versions used for this run

Python 3.12.4, scikit-learn 1.5.1, pandas 2.2.2, numpy 2.0.2, joblib 1.4.2.

## Experiment not run (and why)

A **geographic or temporal holdout** experiment was not run because no dataset
with a usable geographic or temporal key and a verifiable licence is present
in this repository. Inventing a regional split from a dataset of unknown
provenance would produce a number with no meaning. This is recorded as
**pending**, not as a result.
