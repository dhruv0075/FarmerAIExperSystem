# Literature review

Every entry below was retrieved and read from the publisher or the PubMed
Central full-text archive during this work session. Bibliographic details
(title, authors, year, venue, DOI) are copied from the source page.

Analysis is labelled explicitly:

- **Author-stated limitation** — the authors say it themselves.
- **Inferred limitation** — our own critical reading, not their claim.

Nothing here is a quotation invented to fill a gap.

---

## L1 — Advancing crop recommendation system with supervised machine learning and explainable artificial intelligence

| Field | Value |
|---|---|
| Title | Advancing crop recommendation system with supervised machine learning and explainable artificial intelligence |
| Authors | Sourabh Shastri, Sachin Kumar, Vibhakar Mansotra, Rohit Salgotra |
| Year | 2025 |
| Venue | *Scientific Reports*, vol. 15, article 25498 |
| Publisher | Nature Portfolio (open access) |
| DOI | 10.1038/s41598-025-07003-8 |
| Link | https://www.nature.com/articles/s41598-025-07003-8 |

**Objective.** Build a crop recommendation model from soil nutrients and
environmental parameters, and make its output explainable to agronomists
rather than presenting an opaque label.

**Dataset.** A public crop recommendation dataset keyed on nutrient (N, P, K)
and environmental parameters — the same feature family as the dataset used in
AgriWise AI.

**Methodology.** Supervised machine learning with Gradient Boosting as the
proposed model, combined with an Explainable AI (XAI) layer that produces
feature-level explanations for each recommendation.

**Metrics.** Accuracy, precision, recall, F1.

**Reported findings.** 99.27% accuracy, 99.32% precision, 99.36% recall,
99.32% F1. The XAI layer is presented as what makes the tool usable by
agronomists, not merely accurate.

**Author-stated limitations.** The paper positions the contribution as
promising results on a benchmark dataset and a reliability aid for
agronomists; it does not claim field validation, and it does not claim that
high benchmark accuracy transfers to a specific region or season.

**Inferred limitations (our analysis).** The reported accuracy is in the same
>0.99 range AgriWise AI measures on its own local dataset. Two independent
studies both exceeding 99% on similar feature sets is a recognised warning
sign: it usually indicates the classes are near-separable in feature space
under the given sampling, not that the model generalises to real fields.
Neither paper reports temporal or geographic holdout.

**Relevance to AgriWise AI.** Directly supports our decision to show *which*
inputs drove a recommendation and to separate model output from agronomic
rules. It also supports treating high local accuracy as an unproven claim
about real-world performance.


## L2 — Machine learning based recommendation of agricultural and horticultural crop farming in India under the regime of NPK, soil pH and three climatic variables

| Field | Value |
|---|---|
| Title | Machine learning based recommendation of agricultural and horticultural crop farming in India under the regime of NPK, soil pH and three climatic variables |
| Authors | Biplob Dey, Jannatul Ferdous, Romel Ahmed |
| Year | 2024 |
| Venue | *Heliyon*, vol. 10, issue 3, e25112 |
| Publisher | Elsevier (open access, CC BY-NC-ND) |
| DOI | 10.1016/j.heliyon.2024.e25112 |
| PMCID | PMC10844259 |
| Link | https://pmc.ncbi.nlm.nih.gov/articles/PMC10844259/ |

**Objective.** Evaluate five ML models for crop selection and for identifying
required nutrients at a given site, and test whether agricultural and
horticultural crops should be modelled together or separately.

**Dataset.** Sourced from the Kaggle repository. Features are NPK, soil pH and
three climatic variables (temperature, rainfall, humidity). Separate
per-crop yield datasets were used for 11 agricultural and 10 horticultural
crops, plus a combined dataset.

**Methodology.** Support Vector Machine, XGBoost, Random Forest, KNN and
Decision Tree, trained on individual and combined datasets.

**Metrics.** Standard classification performance on held-out data.

**Reported findings.** The accessible PubMed Central abstract states that
XGBoost demonstrated the highest level of accuracy among the five evaluated
models. It reports precision rates of 99.09% for agricultural crops, 99.3%
for horticultural crops and 98.51% for the combined dataset, with AUC values
of 1.0, 1.0 and 0.99, respectively. The authors strongly suggest evaluating
the individual datasets separately by crop category rather than combining
agricultural and horticultural datasets. These are author-reported abstract
results, not metrics reproduced in this project.

**Author-stated limitations.** The dataset is a Kaggle repository dataset; the
authors do not establish its collection geography, sampling protocol or field
provenance. Conclusions are framed around model efficacy on that dataset.

**Inferred limitations (our analysis).** The explicit finding that pooling
crop categories degrades results is the most transferable result for us: it is
a direct argument that a single flat classifier over heterogeneous crops
encodes a strong assumption about homogeneous sampling. It also confirms that
"Kaggle-sourced" is a distribution statement, not provenance.

**Relevance to AgriWise AI.** Justifies documenting that our 22-class model
pools tree, field, pulse and fruit crops trained on data of unresolved
origin, and that class pooling is a real threat to validity rather than a
stylistic choice.

---

## Comparison with AgriWise AI

AgriWise AI is **not** claimed to outperform either paper. This is not a
controlled comparison: different dataset, different split, different code.

| Dimension | L1 (Shastri et al. 2025) | L2 (Dey et al. 2024) | AgriWise AI (this repository) |
|---|---|---|---|
| Task | Crop classification + XAI | Crop classification, pooled vs separate | Crop classification, 22 pooled classes |
| Features | N, P, K + environment | NPK, pH, temperature, rainfall, humidity | N, P, K, temperature, humidity, pH, rainfall |
| Best model | Gradient Boosting | XGBoost (per accessible abstract) | Random Forest |
| Reported accuracy | 0.9927 | Not reproduced here | 0.9955 held-out |
| Explainability | Yes, XAI layer | Not reported | Feature-contribution narrative + rule trace |
| Weather integration | Static features | Static features | Live forecast + advisory rules |
| Lifecycle support | Not reported | Not reported | Stages, activities, reminders |
| Market integration | Not reported | Not reported | Official mandi adapter (currently unverified live) |
| Geographic validation | Not reported | Not reported | Not performed |
| Temporal validation | Not reported | Not reported | Not performed |

"Not reported" means the paper does not address the dimension. It is not a
claim that the work is deficient.
