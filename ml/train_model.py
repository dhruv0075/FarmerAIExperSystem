from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.crop_ml_service import train_and_save_crop_models

DATASET_PATH = ROOT_DIR / "data" / "Crop_recommendation.csv"
MODEL_PATH = ROOT_DIR / "ml" / "crop_model.pkl"
METRICS_PATH = ROOT_DIR / "ml" / "model_metrics.json"
CONFUSION_MATRIX_PATH = ROOT_DIR / "ml" / "confusion_matrix.png"

if __name__ == "__main__":
    print(f"Loading dataset from: {DATASET_PATH}")
    metrics = train_and_save_crop_models(
        data_path=DATASET_PATH,
        model_output_path=MODEL_PATH,
        metrics_output_path=METRICS_PATH,
        cm_image_path=CONFUSION_MATRIX_PATH,
    )
    print("==================================================")
    print("MODEL TRAINING & EVALUATION REPORT")
    print("==================================================")
    print(f"Dataset Size: {metrics['dataset_size']} rows across {len(metrics['crop_classes'])} crop classes")
    print(f"Selected Best Model: {metrics['best_model']}")
    print(f"Best Macro F1 Score: {metrics['best_f1_score']}")
    print("--------------------------------------------------")
    print("Models Evaluated:")
    for res in metrics["models_evaluated"]:
        print(f" - {res['model_name']:<20}: Acc={res['accuracy']:.4f}, Macro-F1={res['macro_f1']:.4f}, CV-Acc={res['cv_accuracy_mean']:.4f} +/- {res['cv_accuracy_std']:.4f}")
    print("--------------------------------------------------")
    print(f"Saved Model: {MODEL_PATH}")
    print(f"Saved Metrics: {METRICS_PATH}")
    print(f"Saved Confusion Matrix: {CONFUSION_MATRIX_PATH}")
    print("==================================================")
