# Research gap

## Candidate gaps and their evidentiary status

Each item below is a **candidate** direction. The status column records what
the reviewed literature and the current system actually support. A candidate
is not promoted to an established gap without evidence.

| # | Candidate gap | Status | Evidence |
|---|---|---|---|
| G1 | Crop recommenders are evaluated on benchmark data without geographic or temporal holdout | **Supported by reviewed papers** | L1 and L2 both report benchmark accuracy and neither reports geographic or temporal validation. Neither reports dataset collection geography. |
| G2 | Pooling heterogeneous crop classes into one flat classifier is a common, under-discussed assumption | **Supported (directly demonstrated)** | L2 explicitly recommends against combining agricultural and horticultural datasets. AgriWise AI pools 22 classes. |
| G3 | Recommendations are static snapshots that do not update as weather and season change | **Partially supported** | L1 and L2 use static feature vectors. AgriWise AI adds live forecast. No reviewed paper demonstrates adaptive re-recommendation, but absence of evidence is not evidence of absence across the whole field. |
| G4 | Crop recommendation is disconnected from lifecycle execution and farmer follow-through | **Not established from reviewed papers** | L1 and L2 are classification studies and do not address lifecycle. This is a gap in *our review coverage*, not a demonstrated gap in the field. A systematic review of decision-support platforms is required before claiming it. |
| G5 | Market price information is rarely joined to the crop decision itself | **Not established** | Only two papers were reviewed. Neither addresses markets, but two papers cannot establish a field-wide gap. |
| G6 | Uncertainty and data limitations are rarely communicated to the farmer | **Partially supported** | L1 addresses explainability, which is adjacent but not the same as communicating *uncertainty*. No reviewed paper reports confidence calibration. |
| G7 | Model confidence is often presented as if it were a probability of agronomic or financial success | **Inferred, not established** | This is a design risk we identified in our own system, not a finding about the literature. |

## What we can honestly claim

1. Two peer-reviewed studies using the same feature family as AgriWise AI both
   report accuracy above 0.99 and neither performs geographic or temporal
   validation (G1).
2. At least one peer-reviewed study explicitly recommends against pooling crop
   categories, which conflicts with the flat 22-class design used here (G2).
3. Explainability has been addressed in the literature for this exact task
   (L1), so an explanation layer in AgriWise AI is an **engineering
   application of an existing technique**, not a novel contribution.

## What we explicitly do NOT claim

- We do not claim AgriWise AI is superior to any reviewed system.
- We do not claim the gaps above are novel discoveries about the field.
- We do not claim any farmer outcome improvement. No field trial or user study
  has been conducted.
- We do not claim G4 or G5 are field-wide gaps; our literature sample is two
  papers.

## Required work before strengthening these claims

- Expand the review to a systematic search across precision-agriculture and
  decision-support venues, with documented search strings and inclusion
  criteria.
- Add a competitor/product analysis sourced from published product
  documentation rather than inferred behaviour.
- Run a geographic or temporal holdout experiment on any regional dataset that
  can be obtained with a verifiable licence.
