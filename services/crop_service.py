from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "data" / "Crop_recommendation.csv"
MODEL_PATH = BASE_DIR / "ml" / "crop_model.pkl"
METRICS_PATH = BASE_DIR / "ml" / "model_metrics.json"
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


def _resolve_dataset_and_target(df: pd.DataFrame):
    target_candidates = ["label", "crop", "Crop"]
    target_name = next((candidate for candidate in target_candidates if candidate in df.columns), None)
    if target_name is None:
        raise ValueError("Dataset must include a target column named 'label' or 'crop'.")

    available = [col for col in FEATURE_COLUMNS if col in df.columns]
    missing = [col for col in FEATURE_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing required feature columns: {missing}")
    return target_name, available


def train_and_save_model(
    data_path: Path | str = DATASET_PATH,
    model_path: Path | str = MODEL_PATH,
    metrics_path: Path | str = METRICS_PATH,
):
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"Training dataset not found: {path}")

    df = pd.read_csv(path)
    target_name, features = _resolve_dataset_and_target(df)
    X = df[features]
    y = df[target_name]

    X = X.apply(pd.to_numeric, errors="coerce")
    y = y.astype(str)
    X = X.fillna(X.median(numeric_only=True))

    stratify = y if y.nunique() > 1 and y.nunique() <= 5 and len(y) >= 2 * y.nunique() else None
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=stratify,
    )

    models = {
        "Decision Tree": DecisionTreeClassifier(random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=200, random_state=42),
        "KNN": KNeighborsClassifier(n_neighbors=min(5, max(1, len(X_train) - 1))),
    }

    metrics = []
    best_model_name = None
    best_model = None
    best_score = -1.0
    best_predictions = None

    for name, model in models.items():
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        report = {
            "model": name,
            "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
            "precision": round(float(precision_score(y_test, predictions, average="weighted", zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, predictions, average="weighted", zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_test, predictions, average="weighted", zero_division=0)), 4),
        }
        metrics.append(report)

        if report["f1_score"] > best_score:
            best_score = report["f1_score"]
            best_model_name = name
            best_model = model
            best_predictions = predictions

    if best_model is None:
        raise RuntimeError("No model could be trained from the provided dataset.")

    model_output = Path(model_path)
    metrics_output = Path(metrics_path)
    model_output.parent.mkdir(parents=True, exist_ok=True)
    metrics_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, model_output)

    model_metrics = {
        "best_model": best_model_name,
        "best_f1_score": round(float(best_score), 4),
        "models": metrics,
        "dataset": path.name,
        "dataset_size": int(len(df)),
        "training_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "features": list(features),
        "crop_classes": sorted(y.unique().tolist()),
        "evaluation": "Single 75/25 train-test split with random_state=42; results are illustrative for the supplied dataset.",
        "confusion_matrix": {
            "labels": sorted(y_test.unique().tolist()),
            "values": confusion_matrix(y_test, best_predictions, labels=sorted(y_test.unique().tolist())).tolist(),
        },
    }
    with metrics_output.open("w", encoding="utf-8") as handle:
        json.dump(model_metrics, handle, indent=2)

    return model_metrics


def ensure_model_exists():
    if not MODEL_PATH.exists() or not METRICS_PATH.exists():
        raise FileNotFoundError("Crop model unavailable. Run python ml/train_model.py.")
    return MODEL_PATH


def predict_crop(features: Dict[str, Any]) -> Dict[str, Any]:
    ensure_model_exists()
    model = joblib.load(MODEL_PATH)
    input_frame = pd.DataFrame(
        [[float(features.get(FEATURE_INPUT_NAMES[column], features.get(column, 0))) for column in FEATURE_COLUMNS]],
        columns=FEATURE_COLUMNS,
    )
    prediction = model.predict(input_frame)[0]
    probability = None
    top_3 = [{"crop": str(prediction), "confidence": None}]

    try:
        probabilities = model.predict_proba(input_frame)[0]
        class_names = model.classes_
        indices = np.argsort(probabilities)[::-1][:3]
        best_index = int(np.argmax(probabilities))
        probability = float(probabilities[best_index]) * 100
        top_3 = [
            {
                "crop": str(class_names[index]),
                "confidence": round(float(probabilities[index]) * 100, 2),
            }
            for index in indices
        ]
    except AttributeError:
        probability = None

    return {
        "recommended_crop": str(prediction),
        "confidence": round(probability, 2) if probability is not None else None,
        "top_3": top_3,
    }


def compare_crop_dataset_fit(features: Dict[str, Any], crop_names: List[str] | None = None) -> List[Dict[str, Any]]:
    dataset = pd.read_csv(DATASET_PATH)
    target_name, columns = _resolve_dataset_and_target(dataset)
    dataset[columns] = dataset[columns].apply(pd.to_numeric, errors="coerce")
    dataset = dataset.dropna(subset=columns + [target_name])
    requested = crop_names or sorted(dataset[target_name].astype(str).unique().tolist())
    results = []
    for crop_name in requested:
        profile_rows = dataset[dataset[target_name].astype(str).str.casefold() == crop_name.casefold()]
        if profile_rows.empty:
            continue
        feature_scores = {}
        for column in columns:
            values = profile_rows[column].astype(float)
            median = float(values.median())
            spread = float(values.quantile(0.75) - values.quantile(0.25))
            if spread <= 0:
                spread = float(dataset[column].std()) or 1.0
            observed = float(features.get(FEATURE_INPUT_NAMES[column], features.get(column, median)))
            match = max(0.0, 100.0 * (1.0 - abs(observed - median) / (2.0 * spread)))
            feature_scores[FEATURE_INPUT_NAMES[column]] = round(match, 1)
        results.append({
            "crop": str(crop_name),
            "dataset_fit": round(sum(feature_scores.values()) / len(feature_scores), 1),
            "feature_scores": feature_scores,
            "sample_count": int(len(profile_rows)),
            "source": DATASET_PATH.name,
        })
    return sorted(results, key=lambda item: item["dataset_fit"], reverse=True)
