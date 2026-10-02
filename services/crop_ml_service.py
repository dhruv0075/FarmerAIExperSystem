from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "data" / "Crop_recommendation.csv"
MODEL_PATH = BASE_DIR / "ml" / "crop_model.pkl"
METRICS_PATH = BASE_DIR / "ml" / "model_metrics.json"
CONFUSION_MATRIX_PATH = BASE_DIR / "ml" / "confusion_matrix.png"

FEATURE_COLUMNS = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
TARGET_COLUMN = "label"

FEATURE_INPUT_NAMES = {
    "N": "nitrogen",
    "P": "phosphorus",
    "K": "potassium",
    "temperature": "temperature",
    "humidity": "humidity",
    "ph": "ph",
    "rainfall": "rainfall",
}


def load_and_validate_dataset(path: Path | str = DATASET_PATH) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset not found at {file_path}")

    df = pd.read_csv(file_path)
    
    # Standardize target column name
    target_col = None
    for candidate in ["label", "crop", "Crop"]:
        if candidate in df.columns:
            target_col = candidate
            break
    if not target_col:
        raise ValueError(f"Dataset missing target column ('label' or 'crop'). Found: {list(df.columns)}")

    # Ensure required features
    missing_features = [col for col in FEATURE_COLUMNS if col not in df.columns]
    if missing_features:
        raise ValueError(f"Dataset missing required feature columns: {missing_features}")

    # Coerce numeric columns
    for col in FEATURE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Clean target string (strip, lowercase)
    df = df.dropna(subset=[target_col])
    df[target_col] = df[target_col].astype(str).str.strip().str.lower()

    # Dataset quality statistics
    null_counts = df[FEATURE_COLUMNS].isnull().sum().to_dict()
    duplicates_count = int(df.duplicated().sum())
    class_counts = df[target_col].value_counts().to_dict()

    valid = np.isfinite(df[FEATURE_COLUMNS]).all(axis=1)
    valid &= (df[["N", "P", "K", "rainfall"]] >= 0).all(axis=1)
    valid &= df["ph"].between(0, 14) & df["humidity"].between(0, 100)
    valid &= df[target_col].ne("")
    invalid_rows = int((~valid).sum())
    df = df.loc[valid].drop_duplicates()

    # Drop any nulls if found
    df = df.dropna(subset=FEATURE_COLUMNS + [target_col])

    quality_summary = {
        "total_rows": int(len(df)),
        "feature_count": len(FEATURE_COLUMNS),
        "target_column": target_col,
        "classes_count": int(df[target_col].nunique()),
        "classes": sorted(df[target_col].unique().tolist()),
        "null_counts": null_counts,
        "duplicate_rows": duplicates_count,
        "invalid_rows_removed": invalid_rows,
        "min_class_samples": int(min(class_counts.values())) if class_counts else 0,
        "max_class_samples": int(max(class_counts.values())) if class_counts else 0,
    }

    return df, quality_summary


def train_and_save_crop_models(
    data_path: Path | str = DATASET_PATH,
    model_output_path: Path | str = MODEL_PATH,
    metrics_output_path: Path | str = METRICS_PATH,
    cm_image_path: Path | str = CONFUSION_MATRIX_PATH,
) -> Dict[str, Any]:
    df, quality_summary = load_and_validate_dataset(data_path)
    target_col = quality_summary["target_column"]

    X = df[FEATURE_COLUMNS]
    y = df[target_col]

    # Stratified 80/20 train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    models = {
        "Decision Tree": DecisionTreeClassifier(max_depth=14, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=16, random_state=42, n_jobs=-1),
        "KNN": make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=5, n_jobs=-1)),
        "Gradient Boosting": HistGradientBoostingClassifier(max_iter=60, random_state=42),
    }

    model_results = []
    best_model_name = None
    best_model_obj = None
    best_f1 = -1.0
    best_predictions = None

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    for name, clf in models.items():
        # 5-Fold cross-validation on training data
        cv_scores = cross_val_score(clf, X_train, y_train, cv=cv, scoring="accuracy")
        cv_acc_mean = float(np.mean(cv_scores))
        cv_acc_std = float(np.std(cv_scores))

        # Train and evaluate on held-out test set
        clf.fit(X_train, y_train)
        preds = clf.predict(X_test)

        acc = float(accuracy_score(y_test, preds))
        macro_prec = float(precision_score(y_test, preds, average="macro", zero_division=0))
        macro_rec = float(recall_score(y_test, preds, average="macro", zero_division=0))
        macro_f1 = float(f1_score(y_test, preds, average="macro", zero_division=0))
        weighted_f1 = float(f1_score(y_test, preds, average="weighted", zero_division=0))

        result_item = {
            "model_name": name,
            "accuracy": round(acc, 4),
            "macro_precision": round(macro_prec, 4),
            "macro_recall": round(macro_rec, 4),
            "macro_f1": round(macro_f1, 4),
            "weighted_f1": round(weighted_f1, 4),
            "cv_accuracy_mean": round(cv_acc_mean, 4),
            "cv_accuracy_std": round(cv_acc_std, 4),
        }
        model_results.append(result_item)

        if macro_f1 > best_f1:
            best_f1 = macro_f1
            best_model_name = name
            best_model_obj = clf
            best_predictions = preds

    if best_model_obj is None:
        raise RuntimeError("No model was successfully trained.")

    # Save best model
    model_out = Path(model_output_path)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    model_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model_obj, model_out)

    # Compute detailed per-class metrics
    labels = sorted(y_test.unique().tolist())
    cm = confusion_matrix(y_test, best_predictions, labels=labels)
    class_report_dict = classification_report(
        y_test, best_predictions, labels=labels, output_dict=True, zero_division=0
    )

    per_class_metrics = {}
    for label in labels:
        if label in class_report_dict:
            per_class_metrics[label] = {
                "precision": round(float(class_report_dict[label]["precision"]), 4),
                "recall": round(float(class_report_dict[label]["recall"]), 4),
                "f1_score": round(float(class_report_dict[label]["f1-score"]), 4),
                "support": int(class_report_dict[label]["support"]),
            }

    # Plot confusion matrix and save as PNG
    try:
        cm_out = Path(cm_image_path)
        cm_out.parent.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(12, 10))
        im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Greens)
        ax.figure.colorbar(im, ax=ax)
        ax.set(
            xticks=np.arange(len(labels)),
            yticks=np.arange(len(labels)),
            xticklabels=[lbl.capitalize() for lbl in labels],
            yticklabels=[lbl.capitalize() for lbl in labels],
            title=f"Crop Recommendation Confusion Matrix ({best_model_name})",
            ylabel="Actual Crop Label",
            xlabel="Predicted Crop Label",
        )
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

        # Loop over data dimensions and create text annotations
        thresh = cm.max() / 2.0
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                val = cm[i, j]
                ax.text(
                    j, i, format(val, "d") if val > 0 else "",
                    ha="center", va="center",
                    color="white" if val > thresh else "black",
                    fontsize=8,
                )
        fig.tight_layout()
        plt.savefig(cm_out, dpi=180, bbox_inches="tight")
        plt.close(fig)
        has_cm_plot = True
    except Exception as e:
        print(f"Warning: Failed to render confusion matrix plot: {e}")
        has_cm_plot = False

    metrics_payload = {
        "best_model": best_model_name,
        "best_f1_score": round(float(best_f1), 4),
        "models_evaluated": model_results,
        "dataset_name": Path(data_path).name,
        "dataset_size": quality_summary["total_rows"],
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "features": FEATURE_COLUMNS,
        "crop_classes": labels,
        "cross_validation": "5-Fold Stratified Cross-Validation on 80% train split",
        "evaluation_protocol": "80/20 Stratified train/test split with random_state=42",
        "per_class_metrics": per_class_metrics,
        "confusion_matrix": {
            "labels": labels,
            "values": cm.tolist(),
        },
        "has_confusion_matrix_plot": has_cm_plot,
        "data_quality_summary": quality_summary,
    }

    metrics_out = Path(metrics_output_path)
    metrics_out.parent.mkdir(parents=True, exist_ok=True)
    with metrics_out.open("w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)

    return metrics_payload


def ensure_crop_model_exists() -> Path:
    if not MODEL_PATH.exists() or not METRICS_PATH.exists():
        raise FileNotFoundError("Crop model unavailable. Run python ml/train_model.py after reviewing dataset provenance.")
    return MODEL_PATH


def predict_crop_ml(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Level 1 ML Prediction:
    Computes ML probabilities across all supported crop classes.
    Returns recommended crop, top 3 candidates, and all class probabilities.
    """
    ensure_crop_model_exists()
    model = joblib.load(MODEL_PATH)

    # Extract feature values safely
    feature_vals = []
    for col in FEATURE_COLUMNS:
        alias = FEATURE_INPUT_NAMES.get(col, col)
        val = features.get(alias, features.get(col, 0.0))
        try:
            val_float = float(val)
        except (ValueError, TypeError):
            val_float = 0.0
        feature_vals.append(val_float)

    input_df = pd.DataFrame([feature_vals], columns=FEATURE_COLUMNS)
    raw_pred = model.predict(input_df)[0]

    probabilities_dict = {}
    top_3 = []
    best_confidence = 0.0

    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(input_df)[0]
        classes = model.classes_
        sorted_indices = np.argsort(probs)[::-1]
        
        for idx in sorted_indices:
            cls_name = str(classes[idx])
            prob_pct = round(float(probs[idx]) * 100.0, 2)
            probabilities_dict[cls_name] = prob_pct

        top_3 = [
            {
                "crop": str(classes[idx]),
                "confidence": round(float(probs[idx]) * 100.0, 2),
            }
            for idx in sorted_indices[:3]
        ]
        best_confidence = top_3[0]["confidence"] if top_3 else 0.0
    else:
        best_confidence = 100.0
        top_3 = [{"crop": str(raw_pred), "confidence": 100.0}]
        probabilities_dict[str(raw_pred)] = 100.0

    return {
        "recommended_crop": str(raw_pred),
        "confidence": best_confidence,
        "top_3": top_3,
        "all_probabilities": probabilities_dict,
        "input_features": dict(zip(FEATURE_COLUMNS, feature_vals)),
    }


def get_model_evaluation_metrics() -> Optional[Dict[str, Any]]:
    if not METRICS_PATH.exists():
        ensure_crop_model_exists()
    if METRICS_PATH.exists():
        try:
            with open(METRICS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

