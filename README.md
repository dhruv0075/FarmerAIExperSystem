# AgriWise AI

AgriWise AI is an intelligent crop lifecycle decision-support system designed for sustainable agriculture. The project combines machine learning for crop recommendation with a rule-based expert system for weather, irrigation, fertilizer, and crop-stage advice. It is built as a simple Flask application using SQLite and an easy-to-understand university-friendly architecture.

## Problem Statement

Farmers often require guidance from crop selection to harvesting, but most systems focus only on one decision area at a time. This project brings together crop recommendation, weather analysis, crop-stage planning, and expert agricultural advice in a single decision-support system.

## Features

- AI-based crop recommendation using a simple machine learning model
- Browser geolocation for farm location detection
- Weather fetch and analysis through the Open-Meteo API
- Crop lifecycle tracking and stage analysis
- Expert system with IF-THEN agricultural rules
- Farmer dashboard with advisory history
- SQLite-backed persistence for users, farms, and records
- Explainable AI outputs that show why a crop was recommended
- Educational agricultural disclaimers and safe decision-support language
- Private Problem Reports with farmer-entered symptoms and reference photos

## Architecture

The application follows a simple layered architecture:

- Browser / Frontend: HTML, CSS, Bootstrap, JavaScript
- Flask Backend: request handling, sessions, validation
- Database: SQLite for users, farms, recommendations, weather, advisories
- ML Layer: trained crop classifier using scikit-learn
- Expert System: rule-based advisory engine for weather and crop management
- Weather Layer: Open-Meteo API integration
- Lifecycle Layer: crop growth stage and harvesting guidance

## Technology Stack

- Python
- Flask
- SQLite
- Pandas
- NumPy
- scikit-learn
- joblib
- requests
- Bootstrap
- Chart.js (optional if used in UI)

## Installation

1. Open a terminal in the project root.
2. Create a virtual environment:
   python -m venv .venv
3. Activate the environment:
   - Windows: .venv\Scripts\activate
4. Install dependencies:
   pip install -r requirements.txt

## Dataset Placement

The crop recommendation model uses the original dataset at:

`data/Crop_recommendation.csv`

The local dataset has 2,200 rows and 22 balanced classes. Its original collection provenance and license are unverified; local benchmark metrics are not evidence of nationwide field accuracy. See docs/data_provenance.md.

For the end-to-end AI/decision-logic implementation, dataset inventory, training steps, and limitations, see [the AI implementation report](docs/ai_implementation_report.md).

## Model Training

Run:

python ml/train_model.py

This script loads the dataset, validates columns, trains multiple models, compares them, and saves the best model to `ml/crop_model.pkl` and experiment metrics to `ml/model_metrics.json`.

## Database Initialization

The database is created automatically when the app starts. SQLite database file:

`database.db`

If it does not exist, the app creates the required tables on startup.

## Running the Application

Start the app:

python app.py

Then open:

http://localhost:5000

## Testing

Run the test suite with:

pytest

This covers authentication, weather parsing, ML behavior, expert rules, lifecycle calculations, and route flow.

## Folder Structure

- `app.py` — main Flask app
- `database.db` — SQLite database
- `requirements.txt` — project dependencies
- `data/Crop_recommendation.csv` — crop classification dataset
- `ml/train_model.py` — training script
- `ml/crop_model.pkl` — trained model
- `ml/model_metrics.json` — training metrics
- `services/` — weather, lifecycle, crop, explanation, and expert services
- `templates/` — Flask HTML templates
- `static/` — CSS and JavaScript
- `tests/` — automated tests

## ML Workflow

1. Load crop dataset
2. Check required feature columns
3. Use a stratified 80/20 train/test split with `random_state=42`
4. Train Decision Tree, Random Forest, KNN, and Histogram Gradient Boosting models
5. Run five-fold stratified cross-validation on training data and select by held-out macro F1
6. Save the best model
7. Use the model for crop prediction in the app

## Expert System Workflow

The expert system analyzes:

- crop stage
- current weather
- soil conditions
- nutrient values
- rainfall and wind trends
- forecast information

It generates recommendations such as irrigation timing, fertilizer planning, disease-risk alerts, and harvest warnings based on IF-THEN rules.

## Weather Workflow

1. Read farm latitude and longitude
2. Call the Open-Meteo API
3. Parse current and future forecast values
4. Store weather information in SQLite
5. Use the weather output in the dashboard and expert system analysis

## Future Scope

- Add a stronger crop yield prediction module
- Add personalized irrigation schedules based on soil moisture sensors
- Add seasonal recommendations and local agronomic knowledge
- Expand lifecycle profiles for more crops
- Add admin views and analytics dashboards

## Disclaimer

AgriWise AI provides decision-support recommendations for educational and planning purposes. Local soil tests, agricultural experts, and official agronomic guidance should be considered before major farming decisions.


## Existing-project repair audit (2026-09-30)

See [requirements audit](docs/requirements_audit.md), [engineering report](docs/engineering_report.md), [API status](docs/api_integrations.md), and [model card](docs/model_cards.md). The master specification is not fully implemented; the audit identifies incomplete workflows separately from unavailable external data.

Local configuration is loaded from ignored `.env`. Set `AGRIWISE_SECRET_KEY` and `DATA_GOV_IN_API_KEY` there, or use environment variables. Never commit credentials. Market access is nonblocking: one background refresh, three bounded retries (0.5/1 second delays), five-minute failure cooldown, 30-minute successful query cache, and five-second spacing for new filter requests. Disk cache retains official source and original fetch timestamp. Status is fresh (<60 seconds), cached (<=30 minutes), stale (>30 minutes), or unavailable. The lock is per application process; multi-worker deployment would need shared locking.

```powershell
python scripts/diagnose_market_api.py
python -m pytest -q
python scripts/browser_check.py
```

The standalone diagnostic prints stages and exception types without credentials. Browser verification requires Playwright and Microsoft Edge. Earlier data.gov.in diagnostics conflict on whether the connection reached TLS; neither established an HTTP response or usable price records. Do not treat either as current status; see [API integration notes](docs/api_integrations.md). Offline weather, generated market/vendor fixtures, fabricated disease probabilities, and unsupported profit estimates are not used as live evidence.


## Historical status and verification (2026-10-14)

The earlier task tracker **[CLINE_PROGRESS.md](CLINE_PROGRESS.md)** recorded
what is IMPLEMENTED, TESTED, VERIFIED and BLOCKED, with the evidence for each.

Results recorded for that earlier snapshot:

- Full automated suite: **145 passed, 0 failed** (`python -m pytest -q`).
- Security regression suite `tests/test_security.py`: **11 passed**.
- Browser automation `scripts/browser_check.py`: **exit code 0**, 19 page checks
  HTTP 200, 0 JavaScript errors, 0 HTTP errors, WebGL scene `ready`.
- Test inventory: [docs/test_inventory.md](docs/test_inventory.md).

These are historical results and do not verify the current homepage redesign.
The latest full test run is recorded below.

Two information-disclosure defects were fixed in the JSON APIs so internal
exception text is never returned to the client; both are covered by regression
tests. A stale selector in `scripts/browser_check.py` was also corrected.

### Research documentation

Research material lives in [docs/research/](docs/research):

| Document | Contents |
|---|---|
| `literature_review.md` | Two peer-reviewed papers, each fetched and read from the publisher or PMC, with verified title, authors, year, venue and DOI, plus author-stated vs inferred limitations |
| `research_gap_evidence.md` | Candidate gaps graded by whether the literature actually supports them |
| `dataset_provenance.md` | Dataset attributes, with provenance explicitly recorded as NOT ESTABLISHED |
| `methodology.md` | Reproducible evaluation protocol, seeds, metrics, software versions and threats to validity |
| `experimental_results.md` | Only results actually produced, plus an explicit list of experiments not run |
| `limitations_and_future_work.md` | Full limitation register and what must never be claimed |
| `research_paper_outline.md` | Section-by-section outline, marked **NOT publication-ready** |

The crop classifier's 0.9955 held-out accuracy is a **local benchmark result**.
The training dataset's provider, licence, collection geography and collection
period are not established, and no geographic or temporal holdout was performed.
No Pune, Maharashtra or India-wide accuracy claim is made or should be inferred.
The standalone disease-image screener has been removed. Problem Report can save
symptoms and a private reference photo but does not analyze the image. There is
no email, SMS or push notification delivery.

## Audit update (2026-10-15)

The full automated test suite was run with
`.\.venv\Scripts\python.exe -m pytest -q --no-header -p no:cacheprovider`:
**164 passed, 1 warning, 0 failed**. The warning is joblib's
Windows physical-core discovery fallback. Importing `app.py` also initializes
the configured default database; during this run that path resolved to
`database.db`. Its contents were not inspected and pre-run file metadata was
not captured, so whether the test run changed existing schema/data is
unknown. See [the research audit](docs/research_audit/README.md) before
rerunning tests against the default data directory.
