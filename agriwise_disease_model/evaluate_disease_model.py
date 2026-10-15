import argparse
import csv
import hashlib
import importlib.util
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

from PIL import Image


UNSUPPORTED_LABEL = "__unsupported__"
ALLOWED_SPLITS = {"calibration", "held-out", "real-world"}
REQUIRED_COLUMNS = {"image_path", "true_class", "dataset_id", "split"}


def _sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(manifest_path, class_names):
    manifest_path = Path(manifest_path).resolve()
    if not manifest_path.is_file():
        raise ValueError(f"Labeled evaluation manifest was not found: {manifest_path}")

    rows = []
    seen_digests = {}
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            required = ", ".join(sorted(REQUIRED_COLUMNS))
            raise ValueError(f"Manifest must contain these columns: {required}")

        for line_number, row in enumerate(reader, start=2):
            image_value = (row.get("image_path") or "").strip()
            true_class = (row.get("true_class") or "").strip()
            dataset_id = (row.get("dataset_id") or "").strip()
            split = (row.get("split") or "").strip()
            if not all((image_value, true_class, dataset_id, split)):
                raise ValueError(f"Manifest line {line_number} has an empty required value.")
            if split not in ALLOWED_SPLITS:
                raise ValueError(
                    f"Manifest line {line_number} has unsupported split {split!r}; "
                    f"use one of {', '.join(sorted(ALLOWED_SPLITS))}."
                )
            if true_class not in class_names and not (
                true_class == UNSUPPORTED_LABEL and split == "real-world"
            ):
                raise ValueError(
                    f"Manifest line {line_number} has unknown class {true_class!r}; "
                    "only real-world rows may use __unsupported__."
                )

            image_path = (manifest_path.parent / image_value).resolve()
            if not image_path.is_file():
                raise ValueError(f"Manifest line {line_number} image was not found: {image_path}")
            digest = _sha256_file(image_path)
            if digest in seen_digests:
                prior_line, prior_split = seen_digests[digest]
                raise ValueError(
                    f"Manifest lines {prior_line} and {line_number} contain duplicate image "
                    f"bytes across or within splits ({prior_split!r}, {split!r})."
                )
            seen_digests[digest] = (line_number, split)
            rows.append(
                {
                    "image_path": image_path,
                    "true_class": true_class,
                    "dataset_id": dataset_id,
                    "split": split,
                }
            )

    if not rows:
        raise ValueError("The evaluation manifest contains no labeled images; no metrics computed.")
    return rows


def _summary(values):
    if not values:
        return {"count": 0, "min": None, "median": None, "mean": None, "max": None}
    return {
        "count": len(values),
        "min": round(min(values), 4),
        "median": round(statistics.median(values), 4),
        "mean": round(statistics.mean(values), 4),
        "max": round(max(values), 4),
    }


def classification_metrics(true_labels, predicted_labels, class_names):
    if len(true_labels) != len(predicted_labels) or not true_labels:
        raise ValueError("Classification metrics require equal, non-empty label sequences.")

    confusion = {label: {predicted: 0 for predicted in class_names} for label in class_names}
    class_metrics = {}
    for label in class_names:
        true_positive = sum(
            actual == label and predicted == label
            for actual, predicted in zip(true_labels, predicted_labels)
        )
        support = sum(actual == label for actual in true_labels)
        predicted_count = sum(predicted == label for predicted in predicted_labels)
        class_metrics[label] = {
            "support": support,
            "precision": round(true_positive / predicted_count, 6) if predicted_count else 0.0,
            "recall": round(true_positive / support, 6) if support else 0.0,
        }
    for actual, predicted in zip(true_labels, predicted_labels):
        if actual not in confusion or predicted not in confusion[actual]:
            raise ValueError("Labels and predictions must be present in the declared class mapping.")
        confusion[actual][predicted] += 1
    correct = sum(actual == predicted for actual, predicted in zip(true_labels, predicted_labels))
    return {
        "sample_count": len(true_labels),
        "accuracy": round(correct / len(true_labels), 6),
        "per_class": class_metrics,
        "confusion_matrix": {
            "labels": list(class_names),
            "counts": [[confusion[actual][predicted] for predicted in class_names] for actual in class_names],
        },
    }


def evaluate_rows(rows, class_names, predictor):
    grouped = {}
    for row in rows:
        with Image.open(row["image_path"]) as source:
            source.load()
            image = source.convert("RGB")
        prediction = predictor(image)
        predicted_class = prediction.get("predicted_class")
        confidence = prediction.get("confidence")
        if predicted_class not in class_names:
            raise ValueError(f"Predictor returned a class outside the mapping: {predicted_class!r}")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 100:
            raise ValueError("Predictor returned an invalid confidence value.")
        key = (row["dataset_id"], row["split"])
        grouped.setdefault(key, []).append(
            {
                "true_class": row["true_class"],
                "predicted_class": predicted_class,
                "confidence": float(confidence),
            }
        )

    reports = []
    for (dataset_id, split), samples in sorted(grouped.items()):
        supported = [sample for sample in samples if sample["true_class"] != UNSUPPORTED_LABEL]
        unsupported = [sample for sample in samples if sample["true_class"] == UNSUPPORTED_LABEL]
        report = {
            "dataset_id": dataset_id,
            "split": split,
            "sample_count": len(samples),
            "confidence_percent": {
                "all": _summary([sample["confidence"] for sample in samples]),
                "correct": _summary(
                    [sample["confidence"] for sample in supported if sample["true_class"] == sample["predicted_class"]]
                ),
                "incorrect": _summary(
                    [sample["confidence"] for sample in supported if sample["true_class"] != sample["predicted_class"]]
                ),
                "by_true_class": {
                    class_name: _summary(
                        [
                            sample["confidence"]
                            for sample in supported
                            if sample["true_class"] == class_name
                        ]
                    )
                    for class_name in class_names
                    if any(sample["true_class"] == class_name for sample in supported)
                },
            },
        }
        if supported:
            report["supported_classification"] = classification_metrics(
                [sample["true_class"] for sample in supported],
                [sample["predicted_class"] for sample in supported],
                class_names,
            )
        if unsupported:
            report["unsupported_input_observations"] = {
                "sample_count": len(unsupported),
                "closed_set_top_class_count": len(unsupported),
                "top_class_distribution": dict(
                    sorted(Counter(sample["predicted_class"] for sample in unsupported).items())
                ),
                "mean_top_confidence_percent": _summary(
                    [sample["confidence"] for sample in unsupported]
                )["mean"],
                "note": (
                    "The classifier always returns a known top class for evaluation; this is "
                    "not an OOD detector or a user-visible accepted prediction."
                ),
            }
        reports.append(report)
    return reports


def _load_predictor(model_dir):
    predictor_path = model_dir / "disease_predictor.py"
    spec = importlib.util.spec_from_file_location("agriwise_evaluation_predictor", predictor_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load the configured disease predictor.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CLASS_NAMES, module.predict_raw


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Evaluate raw MobileNetV3 top-class outputs on a labeled CSV manifest."
    )
    parser.add_argument("--manifest", required=True, help="CSV manifest path.")
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory containing disease_predictor.py, class_names.json, and best_model.pth.",
    )
    parser.add_argument("--output", type=Path, help="Optional path for a JSON report.")
    args = parser.parse_args(argv)

    try:
        model_dir = args.model_dir.resolve()
        class_names, predictor = _load_predictor(model_dir)
        rows = load_manifest(args.manifest, class_names)
        report = {
            "model_directory": str(model_dir),
            "checkpoint_sha256": _sha256_file(model_dir / "best_model.pth"),
            "class_mapping_sha256": _sha256_file(model_dir / "class_names.json"),
            "class_count": len(class_names),
            "class_names": class_names,
            "preprocessing": {
                "input_color": "RGB",
                "resize": [224, 224],
                "normalization_mean": [0.485, 0.456, 0.406],
                "normalization_std": [0.229, 0.224, 0.225],
            },
            "reports": evaluate_rows(rows, class_names, predictor),
            "limitations": [
                "Evaluation reports raw closed-set top-class outputs, not a calibrated user-visible prediction policy.",
                "A real-world unsupported label set measures top-class behavior but does not make the classifier an OOD detector.",
                "Manifest split separation cannot prove that images were absent from the model's training data; dataset provenance must be supplied by the evaluator.",
            ],
        }
        output = json.dumps(report, indent=2, ensure_ascii=False)
        if args.output:
            args.output.write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Evaluation not completed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
