# Machine-learning and dataset audit

**Evidence basis:** current source, committed data/artifact metadata, existing
project documentation, and focused read-only inventory. Model training was
not run as part of this audit.

## 1. Crop classification

### Dataset inventory

| Property | Verified value |
|---|---|
| Primary path | [`data/Crop_recommendation.csv`](../../data/Crop_recommendation.csv) |
| Rows / classes | 2,200 rows, 22 classes, 100 rows per class |
| Columns | `N`, `P`, `K`, `temperature`, `humidity`, `ph`, `rainfall`, `label` |
| Crop labels | apple, banana, blackgram, chickpea, coconut, coffee, cotton, grapes, jute, kidneybeans, lentil, maize, mango, mothbeans, mungbean, muskmelon, orange, papaya, pigeonpeas, pomegranate, rice, watermelon |
| Duplicate CSV | [`data/recommendationData.csv`](../../data/recommendationData.csv) has the same SHA-256 as the primary file in the audited checkout; it is a duplicate copy, not an independent sample. |
| Provenance | Original provider, license, collection protocol, geography and time period are not established by repository evidence. |

Source references: [`load_and_validate_dataset`](../../services/crop_ml_service.py#L45),
[`train_and_save_crop_models`](../../services/crop_ml_service.py#L105), and
[`ml/train_model.py`](../../ml/train_model.py).
Dataset quality documentation is in
[`docs/data_provenance.md`](../data_provenance.md), which correctly marks
provenance unresolved.

The dataset's balance and schema are inspectable; neither proves the rows are
independent field observations. Do not identify its publisher based on
similarity to a widely circulated crop-recommendation benchmark.

### Training and evaluation path

`python ml/train_model.py` calls `train_and_save_crop_models` in
`services/crop_ml_service.py`. The implementation:

1. Reads the CSV and requires the seven named features plus a target column.
2. Coerces features to numeric; strips/lowercases labels; excludes invalid,
   non-finite, out-of-range and duplicate rows.
3. Uses a stratified 80/20 split with `random_state=42`.
4. Evaluates Decision Tree, Random Forest, KNN with `StandardScaler` in a
   pipeline, and Histogram Gradient Boosting.
5. Runs five-fold stratified accuracy cross-validation on the training
   partition.
6. Selects the candidate using macro F1 on the held-out test partition.
7. Saves the winning model, metrics and confusion matrix to `ml/`.

The held-out portion participates in model comparison and winner selection.
Therefore the reported test score is a model-development result and should
not be represented as an untouched, final, independent evaluation. No
geographic or temporal holdout is present. There is no field evaluation.

### Active serving path and parallel implementation

The authenticated `/crop-recommendation` route calls
`services.crop_service.predict_crop` and then
`services.explanation_service.build_explanation`; the saved artifact is
`ml/crop_model.pkl`. The active CLI trainer is instead
`services.crop_ml_service.train_and_save_crop_models`.

`services/crop_service.py` also defines an older, distinct
`train_and_save_model` implementation (different candidate set, split and
selection details). It is not the function called by `ml/train_model.py`.
`predict_crop_ml` and `rank_and_explain_crops` are additional code paths and
are not called by the main `/crop-recommendation` request handler. Avoid
combining results from these paths without identifying which is being
measured.

The prediction wrapper may report a class probability-derived score. The
repository's model card explicitly warns that it is not calibrated field
confidence. A high score is not probability of successful harvest, yield,
profit or agronomic suitability.

### Recorded model metrics

The checked-in [`ml/model_metrics.json`](../../ml/model_metrics.json) and
[`docs/ai_implementation_report.md`](../ai_implementation_report.md) report:

| Candidate | Held-out accuracy | Held-out macro F1 | CV accuracy mean ± SD |
|---|---:|---:|---:|
| Decision Tree | 0.9818 | 0.9817 | 0.9841 ± 0.0073 |
| Random Forest | **0.9955** | **0.9955** | 0.9943 ± 0.0051 |
| KNN | 0.9795 | 0.9793 | 0.9653 ± 0.0121 |
| Histogram Gradient Boosting | 0.9886 | 0.9886 | 0.9926 ± 0.0043 |

These are **reported artifact values**, not newly reproduced training
results. Training was deliberately not invoked because it writes/overwrites
model, metrics and confusion-matrix artifacts. See
[TESTING_AUDIT.md](TESTING_AUDIT.md) for the current test run, whose
`test_ml.py` test uses `tmp_path` outputs.

### Validity limits

- Dataset origin and intended target population unknown.
- Random split permits geographic/temporal/source-batch overlap.
- Test data is used to choose the winner.
- No independent external validation, calibration, field trial, yield or
  farmer-outcome measure.
- Classifier's seven inputs and target are benchmark features/labels; they do
  not encode all locally relevant constraints.
- No inference on nationwide performance is justified.

## 2. Conditional market-price regression

[`forecast_commodity_price`](../../services/market_forecast_service.py#L13)
uses the official market adapter's parsed records, not the generated
`data/market_data.json` fixture. It:

- requires at least 20 distinct daily observations in one market/variety
  series;
- regresses elapsed day against modal price;
- holds out the last 20% chronologically for MAE/RMSE, then refits on all
  available observations;
- bounds the point estimate to ±25% of the latest modal price; and
- derives a heuristic range from RMSE and a percentage floor, explicitly not
  a confidence interval.

No saved training data/model artifact or measured forecast error from a live
usable provider history is established. The live data provider has not been
verified to return a usable record set in this environment. Thus this
component is conditional software behavior, not verified operational
forecasting.

## 4. Rules, calculations and configured reference data

| Component | Evidence and classification |
|---|---|
| Expert advisories | [`expert_system.py`](../../services/expert_system.py): explicit conditions/rules; not learned from labeled examples. |
| Daily plan | [`decision_orchestrator.py`](../../services/decision_orchestrator.py): combines active rules, weather, activity state, risk and market context. Deterministic decision composition. |
| Risk/condition scores | [`risk_service.py`](../../services/risk_service.py): weighted threshold arithmetic and evidence/reason text; scores are locally designed indices, not statistically validated probabilities. |
| Crop suitability | [`suitability_service.py`](../../services/suitability_service.py): configured crop ranges/weights and arithmetic. |
| Crop lifecycle/activity | [`lifecycle_service.py`](../../services/lifecycle_service.py), [`activity_service.py`](../../services/activity_service.py): configured stage durations, task templates, dates and status transitions. |
| Fertilizer advice | [`fertilizer_service.py`](../../services/fertilizer_service.py): thresholds and in-code product/nutrient reference entries; not trained and not a substitute for a verified soil test or local extension advice. |
| Crop profiles | `data/crop_knowledge.json`: local configured reference data, documented as lacking precise, traceable references; ranges are unvalidated educational heuristics. |

No evidence was found of an LLM/chatbot, crop-yield model, or automatic
retraining from farmers' activities, reports, expenses or sales.

## 5. Complete data-source inventory

| Source | What it contains | Use/status |
|---|---|---|
| `data/Crop_recommendation.csv` | 2,200 labeled rows / 22 crop classes / seven numeric features. | Active crop-model training input. Provenance unresolved. |
| `data/recommendationData.csv` | Byte-identical copy per SHA-256 comparison in this checkout. | Not independent data; no active Python loader reference established. |
| `data/crop_knowledge.json` | Configured crop attributes/ranges. | Rules/reference data, not model examples; sources are not fully traceable. |
| `data/market_data.json` | Locally generated market sample. | Excluded by active market service; not live prices or forecast evidence. |
| `data/resource_catalog.json` | Locally generated resources/vendors. | Active resource loader returns an empty list rather than presenting generated entries as verified suppliers. |
| SQLite farmer records | Farms, soil inputs, cycles, activities, expenses/sales, reports and more. | User-entered/operational state, not classifier training data. |
| Open-Meteo | Modeled current conditions and forecast. | Weather context, not on-farm sensor measurements or supervised labels. |
| `data.gov.in` / Agmarknet | External government price records. | Configured adapter; requests 10 records at a time; requires API key; a prior check timed out at HTTP response stage after DNS/TCP/TLS. Usable records remain unverified. |
| `ml/crop_model.pkl`, `ml/model_metrics.json`, `ml/confusion_matrix.png` | Derived crop classifier/evaluation artifacts. | Inference and evaluation outputs, not raw data. |

No automated pipeline was found that folds farmer records into the
classification training datasets.

## 6. Safe next research steps

1. Obtain a traceable source citation, license and collection metadata for
   crop training data; use a geographically/time-separated external dataset
   for final evaluation.
2. Reserve an untouched test set before model selection; report per-class
   metrics, confidence intervals where justified, calibration and errors.
3. Evaluate price forecasts only after verified, sufficiently long and
   timestamped official-market series exist; compare with simple baselines
   and report a true temporal protocol.
4. Validate rules and configured agronomic values with qualified local
   experts; distinguish expert-reviewed content from developer-authored
   heuristics.
