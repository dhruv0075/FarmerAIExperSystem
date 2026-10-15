# Dataset provenance

## Crop recommendation dataset

| Attribute | Status |
|---|---|
| Path | `data/Crop_recommendation.csv` |
| Rows | 2200 |
| Classes | 22 (apple, banana, blackgram, chickpea, coconut, coffee, cotton, grapes, jute, kidneybeans, lentil, maize, mango, mothbeans, mungbean, muskmelon, orange, papaya, pigeonpeas, pomegranate, rice, watermelon) |
| Rows per class | exactly 100 |
| Features | N, P, K, temperature, humidity, ph, rainfall |
| Target | `label` |
| Null feature values | 0 |
| Exact duplicate rows | 0 |
| Provider / publisher | **NOT ESTABLISHED** |
| Licence | **NOT ESTABLISHED** |
| Collection geography | **NOT ESTABLISHED** |
| Collection period | **NOT ESTABLISHED** |
| Sampling protocol | **NOT ESTABLISHED** |
| Field representativeness | **NOT ESTABLISHED** |
| Measurement units for N/P/K | **NOT ESTABLISHED** |

### Why provenance is unresolved

The file was supplied with the project. It was not downloaded by this work and
carries no embedded licence, DOI, or collection note. It resembles widely
circulated benchmark files of the same name, but **resemblance is not
provenance**. Publishing an accuracy figure derived from it does not establish
where the rows came from.

### Consequences that follow from this

1. No geographic accuracy claim is defensible. In particular, **no Pune,
   Maharashtra or India-wide accuracy claim is made anywhere in this
   repository**, and none should be inferred.
2. The 100-per-class balance is a property of construction, not of the field.
   Real crop distributions are imbalanced, so prior probabilities in
   deployment will not match training.
3. Because units for N/P/K are unstated, a farmer's laboratory report may not
   be directly comparable to the training features.
4. A random train/test split on data of unknown collection structure cannot be
   shown to be leakage-free.

### What would resolve it

- A citable source or DOI for the dataset.
- The collection protocol, including whether values were measured or imputed.
- Geographic coordinates or at minimum district/state per row.
- A licence permitting research and redistribution.

## Locally configured knowledge

`data/crop_knowledge.json` holds hand-configured crop profiles and thresholds
consumed by suitability, fertilizer, activity, lifecycle, profit and
crop-decision helpers. Precise traceable agronomic references are missing.
Treat all ranges as **educational heuristics**, not prescriptions. Unit
compatibility with real soil laboratory reports is unverified.

## Excluded fixtures

`data/market_data.json` and `data/resource_catalog.json` were generated
locally. They are retained for audit but are **not** loaded by any operational
path. No price, stock, seller identity or historical observation may be
inferred from them.

## Weather data

Open-Meteo returns **modeled** conditions and forecasts, not on-farm sensor
observations. This is labelled in the UI and must not be presented as measured
field data.

## Farmer-entered data

Farm profile, soil values, activities, expenses, sales and symptom reports are
explicitly farmer-entered. The application distinguishes measured from
estimated values where the farmer has provided that distinction.

## Disease data and model

A 38-class PlantVillage checkpoint and class mapping are included, but the
original training dataset files, training configuration, and independent
labeled evaluation manifest are not included. The checkpoint metadata is not
independent verification of accuracy. User-facing disease labels remain
suppressed until the model is calibrated and evaluated on separate labeled
data.
