# Crop model card

Purpose: educational crop-class classification using seven dataset features. Not for selecting pesticide doses, guaranteeing yield/profit, or nationwide agronomic suitability.

Dataset: `data/Crop_recommendation.csv`; 2,200 rows, 22 balanced classes (100/class). The provider, license, collection geography and time period are unverified. The recorded evaluation uses 1,760 training and 440 test rows, stratified 80/20 split, seed 42; five-fold stratified cross-validation is performed on the training split. KNN scaling stays inside its pipeline. Invalid records and exact duplicates are filtered before training.

Selection uses held-out macro F1, so the held-out data is also used to select the winning model; this is a development benchmark, not an independent final evaluation. A nested selection protocol and external geographic/temporal holdout are future work. Class probabilities are not calibrated field confidence. Exact recorded metrics and confusion matrix: `ml/model_metrics.json` and `ml/confusion_matrix.png`. Training was not repeated for the 2026-10-15 audit.

Disease screening: a MobileNetV3 Small checkpoint and 38-class mapping are present, and the standalone Disease Detection route can call the predictor when its optional dependencies are available. The output is only an unverified closest-class suggestion for a matching crop. Checkpoint training lineage and dataset split are unknown; no calibration or independent evaluation manifest is present, so accuracy, calibration and field performance are unmeasured. The separate Problem Report flow stores symptoms and an optional reference image; it is not the standalone image-screening workflow. See `disease_detection.md`.

Price forecast: conditional on sufficient official market history. The code requires at least 20 distinct daily observations from one market/variety series. No live usable history or measured forecast accuracy is established; the forecast remains unavailable when the required data is absent.

## Actual training results

| Model | Accuracy | Macro F1 | CV accuracy mean +/- SD |
|---|---:|---:|---:|
| Decision Tree | 0.9818 | 0.9817 | 0.9841 +/- 0.0073 |
| Random Forest | 0.9955 | 0.9955 | 0.9943 +/- 0.0051 |
| KNN | 0.9795 | 0.9793 | 0.9653 +/- 0.0121 |
| Histogram Gradient Boosting | 0.9886 | 0.9886 | 0.9926 +/- 0.0043 |

These values are reported from the checked-in metrics artifact and reflect the protocol above. They do not establish field accuracy or nationwide suitability.
