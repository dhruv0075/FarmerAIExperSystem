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

The project expects a crop dataset at:

`data/Crop_recommendation.csv`

The local dataset has 2,200 rows and 22 balanced classes. Its original collection provenance and license are unverified; local benchmark metrics are not evidence of nationwide field accuracy. See docs/data_provenance.md.

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
3. Split data into training and validation sets
4. Train Decision Tree, Random Forest, and KNN models
5. Compare metrics such as accuracy, precision, recall, and F1 score
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

The standalone diagnostic prints stages and exception types without credentials. Browser verification requires Playwright and Microsoft Edge. Government API currently fails at TCP connection, before TLS/authentication. Offline weather, generated market/vendor fixtures, fabricated disease probabilities, and unsupported profit estimates are not used as live evidence.
