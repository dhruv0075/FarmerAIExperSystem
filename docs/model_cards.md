# Crop model card

Purpose: educational crop-class classification using seven dataset features. Not for selecting pesticide doses, guaranteeing yield/profit, or nationwide agronomic suitability.

Dataset: local Crop_recommendation.csv; collection provenance unverified. 1760 training and 440 test rows, stratified 80/20 split, seed 42. Five-fold stratified cross-validation on training split. KNN scaling stays inside its pipeline. Missing/invalid records and duplicates filtered before training.

Selection currently uses held-out macro F1; a nested selection protocol and external geographic/temporal holdout are future work. Class probabilities are not calibrated field confidence. Exact metrics and confusion matrix: ml/model_metrics.json and ml/confusion_matrix.png.

Disease: no validated model installed; active route records symptoms and image attachments for expert review without diagnostic confidence. Price forecast: unavailable without sufficient comparable official history; no measured forecast accuracy is claimed.

## Actual training results

| Model | Accuracy | Macro F1 | CV accuracy mean ? SD |
|---|---:|---:|---:|
| Decision Tree | 0.9818 | 0.9817 | 0.9841 ? 0.0073 |
| Random Forest | 0.9955 | 0.9955 | 0.9943 ? 0.0051 |
| KNN | 0.9795 | 0.9793 | 0.9653 ? 0.0121 |
| Gradient Boosting | 0.9886 | 0.9886 | 0.9926 ? 0.0043 |
