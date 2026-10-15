# Crop Disease Detection

## User workflow

1. Use the separate **Disease Detection** page (`/disease-detection`) to choose a crop and upload a leaf photo.
2. The server validates the image and runs the supplied MobileNetV3 Small checkpoint in memory. This page does not save the image or create a Problem Report.
3. The page shows the model's closest PlantVillage class as an **unverified suggestion** only when its crop matches the selected crop. Unsupported crops, including Rice, do not receive a suggestion.
4. Use **Problem Report** (`/report-problem`) separately to save symptoms and an optional private reference photo. It does not run the image model.

Image screening is advisory only and does not replace a qualified local agricultural expert.

## Viewing the full dataset

The full PlantVillage dataset is hosted on [Hugging Face](https://huggingface.co/datasets/mohanty/PlantVillage). Open its Dataset viewer to browse examples, labels, and image rows. The `color` configuration contains the original RGB images. The full collection has 54,306 images; it is **not bundled** in this project. The Disease Detection page also lists the 38 class labels used by the bundled checkpoint. This smaller label list is not the full image dataset.

To download and inspect a local copy, install the optional `datasets` package and load the color configuration:

```powershell
python -m pip install datasets
python -c "from datasets import load_dataset; ds=load_dataset('mohanty/PlantVillage','color'); print(ds); print(ds['train'][0]['label']); ds['train'][0]['image'].show()"
```

Loading the full configuration downloads the dataset and may require substantial storage.

## Optional installation

Install the disease-model dependencies:

```powershell
pip install -r requirements-disease.txt
```

Without the optional model packages or checkpoint, Problem Report still works independently and Disease Detection reports that screening could not run.

## Model scope and evaluation

The model checkpoint has 38 PlantVillage classes and does not include Rice. Its raw top-class output is a closed-set classifier: it has no validated out-of-distribution detector, and a high softmax score is not a calibrated probability. The UI may show the top class only as an unverified suggestion when its crop matches the crop selected on the Disease Detection page; mismatched crop suggestions are suppressed. The UI labels its raw softmax value as a model score, not as accuracy or probability. Do not use `model_info.json` figures or sample-image predictions as a verified user-facing accuracy score.

No labeled calibration, independent held-out, or real-world evaluation manifest is included with the supplied artifacts. Consequently, this repository does **not** claim an accuracy score. The available sample images support only inference smoke tests, not accuracy measurement. The evaluator requires a labeled CSV with `image_path`, `true_class`, `dataset_id`, and `split` columns; allowed splits are `calibration`, `held-out`, and `real-world`. The evaluator rejects missing/empty manifests and duplicate image bytes across splits. A real-world `__unsupported__` label measures closed-set behavior only; it does not establish OOD detection.

After preparing separate, provenance-documented datasets, run:

```powershell
python agriwise_disease_model/evaluate_disease_model.py --manifest <path-to-labeled-manifest.csv> --output <path-to-report.json>
```

Calibration and held-out data must be separate. Do not treat the displayed suggestion as a verified prediction unless thresholds and coverage have been measured on calibration data and the resulting policy has been checked on independent held-out data.

## Verification status

The real checkpoint was loaded and exercised on a synthetic image and through the standalone authenticated Disease Detection route. The focused disease-screening integration tests pass. These are runtime/workflow correctness checks, not a disease-accuracy measurement. No labeled calibration, held-out, or real-world manifest is present, so accuracy, precision, recall, calibration, and field performance remain **unmeasured**.
