import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image

try:
    from agriwise_disease_model.evaluate_disease_model import (
        UNSUPPORTED_LABEL,
        classification_metrics,
        evaluate_rows,
        load_manifest,
    )
except ModuleNotFoundError:  # pragma: no cover - supports direct discovery execution
    from evaluate_disease_model import (
        UNSUPPORTED_LABEL,
        classification_metrics,
        evaluate_rows,
        load_manifest,
    )


class EvaluationMetricsTests(unittest.TestCase):
    def test_reports_accuracy_per_class_and_confusion_matrix(self):
        metrics = classification_metrics(
            ["healthy", "blight", "blight"],
            ["healthy", "healthy", "blight"],
            ["healthy", "blight"],
        )

        self.assertAlmostEqual(metrics["accuracy"], 2 / 3, places=6)
        self.assertEqual(metrics["per_class"]["healthy"]["precision"], 0.5)
        self.assertEqual(metrics["per_class"]["blight"]["recall"], 0.5)
        self.assertEqual(metrics["confusion_matrix"]["counts"], [[1, 0], [1, 1]])

    def test_requires_non_empty_matched_label_sequences(self):
        with self.assertRaises(ValueError):
            classification_metrics([], [], ["healthy"])
        with self.assertRaises(ValueError):
            classification_metrics(["healthy"], [], ["healthy"])


class EvaluationManifestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def _write_manifest(self, rows):
        path = self.root / "manifest.csv"
        with path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(
                output,
                fieldnames=["image_path", "true_class", "dataset_id", "split"],
            )
            writer.writeheader()
            writer.writerows(rows)
        return path

    def _write_image(self, name, color):
        image_path = self.root / name
        Image.new("RGB", (12, 12), color).save(image_path, format="PNG")
        return image_path

    def test_loads_separate_labeled_rows(self):
        self._write_image("leaf-a.png", "green")
        manifest = self._write_manifest(
            [
                {
                    "image_path": "leaf-a.png",
                    "true_class": "healthy",
                    "dataset_id": "plantvillage-heldout",
                    "split": "held-out",
                }
            ]
        )

        rows = load_manifest(manifest, ["healthy", "blight"])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["true_class"], "healthy")
        self.assertEqual(rows[0]["split"], "held-out")

    def test_rejects_missing_labels_unknown_classes_and_invalid_splits(self):
        self._write_image("leaf-a.png", "green")
        cases = [
            {"image_path": "leaf-a.png", "true_class": "", "dataset_id": "ds", "split": "held-out"},
            {"image_path": "leaf-a.png", "true_class": "other", "dataset_id": "ds", "split": "held-out"},
            {"image_path": "leaf-a.png", "true_class": "healthy", "dataset_id": "ds", "split": "train"},
        ]
        for row in cases:
            with self.subTest(row=row):
                manifest = self._write_manifest([row])
                with self.assertRaises(ValueError):
                    load_manifest(manifest, ["healthy", "blight"])

    def test_unsupported_label_is_real_world_only(self):
        self._write_image("object.png", "brown")
        manifest = self._write_manifest(
            [
                {
                    "image_path": "object.png",
                    "true_class": UNSUPPORTED_LABEL,
                    "dataset_id": "unrelated-objects",
                    "split": "real-world",
                }
            ]
        )

        rows = load_manifest(manifest, ["healthy", "blight"])
        report = evaluate_rows(
            rows,
            ["healthy", "blight"],
            lambda _image: {"predicted_class": "blight", "confidence": 95.0},
        )
        self.assertEqual(report[0]["unsupported_input_observations"]["sample_count"], 1)
        self.assertEqual(
            report[0]["unsupported_input_observations"]["closed_set_top_class_count"],
            1,
        )
        self.assertIn("not an OOD detector", report[0]["unsupported_input_observations"]["note"])

    def test_rejects_duplicate_image_bytes_across_splits(self):
        self._write_image("leaf-a.png", "green")
        manifest = self._write_manifest(
            [
                {"image_path": "leaf-a.png", "true_class": "healthy", "dataset_id": "ds", "split": "calibration"},
                {"image_path": "leaf-a.png", "true_class": "healthy", "dataset_id": "ds", "split": "held-out"},
            ]
        )

        with self.assertRaisesRegex(ValueError, "duplicate image"):
            load_manifest(manifest, ["healthy", "blight"])

    def test_unavailable_manifest_reports_no_metrics(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            load_manifest(self.root / "missing.csv", ["healthy"])


if __name__ == "__main__":
    unittest.main()
