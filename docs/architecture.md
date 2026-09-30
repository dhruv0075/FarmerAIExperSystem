# Architecture

Existing Flask app factory and route layer in app.py, SQLite connection/migrations in db.py, modular services, Jinja templates, Bootstrap/Chart.js/Leaflet frontend. FarmState aggregates farmer/farm/soil/cycle/weather/activity/problem/finance data. The orchestrator calls expert, risk and market services. Confirmed activities are separate from pending recommendations.

No microservices or architecture replacement was introduced. Some older duplicate ML/risk pathways remain and need consolidation after contract coverage. The system is a research prototype, not a validated autonomous agronomy service.
