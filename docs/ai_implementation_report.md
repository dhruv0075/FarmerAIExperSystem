# AgriWise AI implementation and data report

**Reviewed:** 2026-10-12
**Scope:** Current repository implementation, bundled data files, persisted model artifacts, and the runtime paths that consume them.

## Executive summary

AgriWise AI is a decision-support web application, not a generative-AI system. Its primary trained machine-learning feature is supervised crop classification: it predicts one of 22 crop labels from seven soil and climate measurements. Crop lifecycle guidance, nutrient checks, weather advisories, risk scores, and explanations are implemented mostly as explicit rules and calculations. A separate linear-regression price-trend forecast is attempted only when enough official market history is available.

The project does **not** currently contain an operational disease-image classifier, a crop-yield model, an LLM/chatbot, or a process that automatically retrains the crop classifier from farmers' activity or harvest outcomes. The disease-report page accepts images for record keeping and expert review; it does not diagnose them with AI.

The model metrics describe performance on the supplied local dataset. The dataset's original provider, collection location/date, and license are not established in the repository, so these scores do not establish field accuracy or nationwide suitability.

## Where AI and decision logic live

| Capability | Main implementation | How it works | Actual application path |
|---|---|---|---|
| Crop classification | [`services/crop_ml_service.py`](../services/crop_ml_service.py), trained by [`ml/train_model.py`](../ml/train_model.py); serialized as [`ml/crop_model.pkl`](../ml/crop_model.pkl) | Trains and evaluates Decision Tree, Random Forest, scaled KNN, and Histogram Gradient Boosting classifiers. Selects the highest held-out macro-F1 model. | The authenticated `/crop-recommendation` route in [`app.py`](../app.py) calls `services.crop_service.predict_crop`, stores the submitted inputs and result, and renders the recommendation. That prediction wrapper loads the shared pickle artifact. |
| Crop recommendation explanation | [`services/explanation_service.py`](../services/explanation_service.py) and [`services/crop_service.py`](../services/crop_service.py) | Compares supplied measurements with per-crop dataset medians and interquartile ranges. It reports profile-match indicators and the classifier's top alternatives; this is not SHAP or a causal explanation. | Called by the crop-recommendation route after prediction. |
| Expert advisories and daily plan | [`services/expert_system.py`](../services/expert_system.py), [`services/decision_orchestrator.py`](../services/decision_orchestrator.py) | Evaluates explicit IF/THEN conditions against weather, forecast, soil, crop-stage, and farmer-confirmed activity facts; orchestration combines advisories with risk and market context. | `/expert-system`, advisory generation, `/daily-plan`, and dashboard paths in [`app.py`](../app.py). |
| Crop and nutrient suitability | [`services/suitability_service.py`](../services/suitability_service.py), [`services/fertilizer_service.py`](../services/fertilizer_service.py) | Uses locally configured crop ranges, thresholds, weighted arithmetic scores, and fixed fertilizer reference data. These are rules/heuristics, not a model trained from examples. | Used by crop decision, fertilizer, activity, lifecycle, and profit-related service paths. |
| Lifecycle and activity planning | [`services/lifecycle_service.py`](../services/lifecycle_service.py), [`services/activity_service.py`](../services/activity_service.py) | Uses crop-stage tables, configured durations, dates, and templates for suggested activities. | Lifecycle and activity routes in [`app.py`](../app.py). |
| Market price forecast | [`services/market_forecast_service.py`](../services/market_forecast_service.py) | Fits a one-variable linear regression to time versus official modal-price observations, evaluates a chronological holdout, and bounds the projection. It refuses to forecast without at least 20 observations. | Market and sell-planner routes in [`app.py`](../app.py), subject to available official-data history. |
| Crop problem / disease report | [`services/disease_service.py`](../services/disease_service.py) | Uses submitted symptom text and limited contextual checks to produce cautious inspection suggestions. Image analysis is explicitly unavailable. | `/report-problem` stores reports/images and sends the result for expert inspection. |
| Weather context | [`services/weather_service.py`](../services/weather_service.py) | Fetches modeled current weather and forecasts from Open-Meteo, with a short-lived cache; it is not a farm sensor feed. | Weather and farm-plan routes; current weather/forecast can be passed to deterministic advice. |

### Important implementation distinction

The current training entry point imports `train_and_save_crop_models` from `services.crop_ml_service`. The main recommendation page instead invokes `predict_crop` from `services.crop_service`, which loads the resulting `ml/crop_model.pkl`. The latter file also contains an older, separate training implementation; it is not the training function selected by `ml/train_model.py`. The repository additionally defines `predict_crop_ml` and `rank_and_explain_crops`; these are separate service paths and are not called by the main `/crop-recommendation` handler.

This split matters when changing or describing training: the metrics and model comparison below are from the active `ml/train_model.py` pipeline and `services/crop_ml_service.py`, not the older alternative implementation.

## Crop classifier: complete workflow

### Training and evaluation

1. **Load data:** `python ml/train_model.py` reads `data/Crop_recommendation.csv`.
2. **Validate schema:** the loader accepts `label`, `crop`, or `Crop` as the target name and requires `N`, `P`, `K`, `temperature`, `humidity`, `ph`, and `rainfall`.
3. **Clean and validate:** feature columns are coerced to numeric; target labels are stripped and lowercased; rows with missing target, non-finite or invalid feature values, out-of-range pH/humidity, negative N/P/K/rainfall, or duplicate records are excluded.
4. **Split:** data is split into 80% training and 20% held-out test data with stratification and `random_state=42`. For the current 2,200-row dataset, that is 1,760 training rows and 440 test rows.
5. **Compare four classifiers:**
   - Decision Tree (`max_depth=14`)
   - Random Forest (`n_estimators=100`, `max_depth=16`)
   - KNN (`k=5`) with `StandardScaler` inside a pipeline
   - Histogram Gradient Boosting (`max_iter=60`)
6. **Cross-validate:** each candidate receives five-fold stratified cross-validation on the training split; the reported cross-validation metric is accuracy.
7. **Select:** candidates are ranked by macro F1 on the held-out test set. The winning already-fitted model is saved as `ml/crop_model.pkl`. The test set is also used to compare/select models, so the displayed held-out result is a development benchmark, not an independent final audit.
8. **Save evaluation output:** `ml/model_metrics.json` records the split, metrics, class labels, per-class results, and confusion matrix. `ml/confusion_matrix.png` visualizes the winning model's test-set confusion matrix.

Run or reproduce training from the project root:

```powershell
python ml/train_model.py
```

Training is not performed automatically when the Flask application starts. The app uses the saved artifact; if required artifacts are missing, prediction reports that the model is unavailable.

### Stored benchmark results

The checked-in [`ml/model_metrics.json`](../ml/model_metrics.json) records the following results. CV values are mean accuracy and standard deviation across the five training folds.

| Candidate | Test accuracy | Test macro F1 | CV accuracy mean +/- SD |
|---|---:|---:|---:|
| Decision Tree | 0.9818 | 0.9817 | 0.9841 +/- 0.0073 |
| Random Forest (selected) | 0.9955 | 0.9955 | 0.9943 +/- 0.0051 |
| KNN | 0.9795 | 0.9793 | 0.9653 +/- 0.0121 |
| Histogram Gradient Boosting | 0.9886 | 0.9886 | 0.9926 +/- 0.0043 |

These are scores on a small, balanced, local benchmark and are not estimates of real-world performance. Classifier probabilities surfaced as “confidence” are not calibrated field-confidence values.

### Prediction at runtime

1. A signed-in farmer submits N, P, K, pH, temperature, humidity, and rainfall on `/crop-recommendation`.
2. The route validates numeric and basic bounds. Moisture can be captured and stored but is **not** one of the classifier's seven input features.
3. `services.crop_service.predict_crop` loads the saved model and sends the seven values, in the required column order, to `predict` and (when supported) `predict_proba`.
4. The response includes the highest-ranked crop, its model probability, and up to three alternatives.
5. `build_explanation` compares each supplied feature with the labelled examples for the recommended crop and adds profile-match context. Those match values are descriptive distances, not probabilities or validated agronomic suitability.
6. The route saves the input to `soil_records` and the prediction, probability, explanation, and input JSON to `crop_recommendations` in SQLite.
7. The farmer separately confirms a selected crop before starting its lifecycle. The app does not treat a recommendation as an automatically planted crop.

The 22 classifier labels are: apple, banana, blackgram, chickpea, coconut, coffee, cotton, grapes, jute, kidneybeans, lentil, maize, mango, mothbeans, mungbean, muskmelon, orange, papaya, pigeonpeas, pomegranate, rice, and watermelon.

## Dataset and data-source inventory

| Data/source | Contents and size | Operational use | Provenance / limitations |
|---|---|---|---|
| [`data/Crop_recommendation.csv`](../data/Crop_recommendation.csv) | 2,200 rows; columns `N`, `P`, `K`, `temperature`, `humidity`, `ph`, `rainfall`, `label`; 22 balanced classes (100 examples per class). | The active crop-classifier training source and crop-profile explanation comparisons. | Original provider, license, geography, and collection period are not verified. Similarity to a circulated benchmark is not provenance evidence. |
| [`data/recommendationData.csv`](../data/recommendationData.csv) | 2,200 rows with the same columns and contents as `Crop_recommendation.csv`; files have identical SHA-256 hashes in the reviewed checkout. | No operational Python loader/reference was found; treat as a duplicate copy, not an additional independent dataset. | Same provenance limitations as the primary CSV. |
| [`data/crop_knowledge.json`](../data/crop_knowledge.json) | Locally configured crop profiles and thresholds for 23 crop keys. | Read by suitability, fertilizer, activity, lifecycle, profit, and crop-decision helpers. | This is hand-configured knowledge, not labelled training data. The repository notes that precise traceable references are missing; treat ranges as educational heuristics, not verified prescriptions. |
| [`data/market_data.json`](../data/market_data.json) | Locally generated sample market/commodity fixture. | Not used by the operational market loader. `market_service` delegates to the official data adapter instead. | Do not infer current prices, stock, seller identities, or historical observations from this fixture. |
| [`data/resource_catalog.json`](../data/resource_catalog.json) | Locally generated resource/vendor fixture. | Bundled catalog loading is disabled; the service returns no bundled listings. | Not a verified supplier directory or source of current price/stock. |
| In-code reference data and rules | Crop-stage profiles, activity templates, expert IF/THEN rules, and fertilizer-composition entries live in service modules rather than dataset files. | Used by lifecycle/activity planning, the expert engine, and nutrient guidance. | These are configured rules/reference values, not model-training examples; verify agronomic values and local applicability. |
| Official mandi data (`data.gov.in` / Agmarknet) | External commodity/market price records; successful query results are cached with source, fetch time, and raw provider records. | Market display and, conditionally, price-forecast input. New successful refreshes are merged with cached records and deduplicated by commodity, market, location, variety, and arrival date. | Each request is limited to a small provider sample (10 records); repeated refreshes do not guarantee coverage or a complete time series. Requires `DATA_GOV_IN_API_KEY`; availability is not guaranteed. The latest single live check completed DNS/TCP/TLS but timed out awaiting HTTP; key acceptance, response format, and usable records remain unverified. It is not a crop-classifier training dataset. |
| Open-Meteo forecast API | Modeled current conditions and forecast fields for farm coordinates. | Weather display and context for farm advisories/plans. | Provider model output, not on-farm sensor measurements or labelled training data. |
| Farmer-entered SQLite records | Farm profile/location, soil values, crop cycles, activity confirmations, problem reports, expenses, and sales. | Personalize calculations and rules; completed activity history can affect later advisory logic. | User-entered operational records. No automatic pipeline adds them to crop-model training. |
| Model/evaluation artifacts | [`ml/crop_model.pkl`](../ml/crop_model.pkl), [`ml/model_metrics.json`](../ml/model_metrics.json), and [`ml/confusion_matrix.png`](../ml/confusion_matrix.png). | The pickle is the deployed crop classifier; JSON/PNG are training outputs for inspection. | Derived artifacts, not source datasets. |

## Other prediction and advisory steps

### Rule-based farm recommendations

1. Farm context is assembled from SQLite (farm profile, latest soil values, active crop cycle, activities, reports, expenses, and sales).
2. Weather is fetched for the farm coordinates when available; cached or stored context may be used in service flows.
3. The expert system derives facts such as wind speed, forecast precipitation, soil N/P/K/moisture, crop stage, and hours since last completed irrigation/fertilizer activity.
4. Explicit rules are evaluated; matching rules produce advisories with recorded evidence and severity.
5. The orchestrator combines these advisories with risk analysis and official market context for the dashboard and daily plan.
6. Recommendations and activities are stored; farmer-confirmed completed actions are distinguished from pending suggestions.

This is an explainable, deterministic expert system. It does not learn the IF/THEN rules from a dataset.

### Price forecast (conditional)

1. Market pages request prices/history through the official market adapter and its bounded cache. Only actual parsed provider observations are used; generated fixture prices are excluded.
2. Successful refreshes merge raw provider records by commodity, market, district, state, variety, and arrival date. Repeated identical refreshes do not add observations. The adapter requests only 10 records at a time, so the cache can remain too small or incomplete.
3. The forecast keeps distinct dates within one market-and-variety series separate from other series. It returns an insufficient-data status without at least 20 observations from the same series; repeated refreshes do not manufacture historical coverage.
4. With enough history, it regresses modal price on elapsed days, holds out the final 20% chronologically for MAE/RMSE, then fits the line to all available observations for a future projection.
5. The point estimate is bounded to +/-25% of the latest modal price; an uncertainty band is constructed from the holdout RMSE and a minimum percentage margin.

The range is explicitly uncalibrated and is not a statistical confidence interval. It should not be presented as a reliable future-price guarantee or evidence of an operational market-history service. Because the forecast depends on actual provider history, it may be unavailable in normal use.

### Lifecycle activities

The lifecycle page and activity-list page lazily create configured activities for the current crop stage. Generation is idempotent for a crop cycle, stage, and activity title; it does not mark suggested work complete. A farmer must separately update an activity's status for it to count as completed history.

### Disease and image reports

The app validates and stores supported image uploads and symptom details. `analyze_crop_issue` can add limited context-based inspection advice, but returns no disease diagnosis, no model confidence, and `model_available: false`. There is no installed/validated disease image model or associated training dataset/metrics.

## Reproduction and verification

From the repository root:

```powershell
python ml/train_model.py
python -m pytest -q
python app.py
```

The report's classifier figures were read from the checked-in `ml/model_metrics.json` and cross-checked against the active training implementation. Dataset provenance caveats are also documented in [`docs/data_provenance.md`](data_provenance.md), API status in [`docs/api_integrations.md`](api_integrations.md), and the model card in [`docs/model_cards.md`](model_cards.md).

## Limitations and safe interpretation

- Recommendations are educational decision support; verify local conditions with soil tests and qualified local agricultural guidance.
- Benchmark accuracy is not field validation, and the source dataset's provenance and geographic representativeness are unknown.
- The classifier's probabilities and profile-match scores are not calibrated risk or suitability guarantees.
- Weather is provider-modeled; soil, activity, expense, and sales data depend on farmer entry.
- Crop ranges and many nutrient/risk thresholds are local heuristics whose agronomic references need stronger verification.
- No disease image classifier, yield predictor, generative AI, or automatic model-learning loop is currently implemented.
