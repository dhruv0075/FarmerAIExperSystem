# Historical engineering handover — 2026-09-30

This is a dated snapshot, not the current status report. Some integration and
test details below have since changed or conflict with other historical
diagnostics. For current source-grounded status, see
[`docs/research_audit/`](research_audit/README.md), especially its API,
model/data and testing audits.

AgriWise was repaired in place and is running locally. It is **not fully compliant with the original master specification**. See requirements_audit.md for COMPLETE/PARTIAL/MISSING/BLOCKED classifications; initially broken items are listed there. No farmer rows were reset or deleted. This report distinguishes runtime verification from unimplemented research ambitions.

1. **Folder structure:** app.py, db.py, requirements.txt, .env.example; services/, templates/, static/, data/, ml/, tests/, scripts/, docs/. Private uploads and ignored artifacts hold images, database/model backups and test evidence.
2. **Pages:** about, activities, advisories, compare_crops, crop_lifecycle, crop_recommendation, daily_plan, dashboard, data_transparency, disease_result, expenses, expert_system, farm_profile, farm_report, farm_setup, fertilizer, history, index, login, market, ml_analytics, notifications, profit_planner, recommendation_result, register, report_problem, research, resources, risk_analysis, sell_planner, settings, seven_day_plan, weather, what_if.
3. **Implemented features:** authentication, farm setup/profile, crop ML, suitability/comparison, lifecycle, weather, rule reasoning, confirmed activities, symptom reports, community resources, actual finances, agronomic what-if, reports and transparency. Module completeness varies in the acceptance audit.
4. **Actions tested:** registration, login/logout, setup redirect/manual save, crop prediction/selection, lifecycle creation, activity completion/skip/harvest/reschedule, expense/sale submission with actual HTML field names, resource submission, problem reporting, invalid-image rejection, CSRF rejection/acceptance, protected page reads. Every visible button has NOT been manually verified.
5. **Database:** 23 `CREATE TABLE IF NOT EXISTS` statements in the current `db.py`; the older count of 24 was incorrect. The “preserved SQLite data” statement refers to the original 2026-09-30 handover and is not a current database integrity verification. Schema documented in database_schema.md.
6. **APIs:** Open-Meteo and Nominatim were reported live verified at the time. Historical data.gov.in diagnostics conflict: one record says TCP failed before TLS, while another says DNS/TCP/TLS completed before the HTTP response timed out. Neither establishes an HTTP response or usable market records; current status remains unverified.
7. **Dataset:** existing data/Crop_recommendation.csv; original provenance/license unverified.
8. **Quality:** 2200 rows, 22 classes, 100/class; zero feature nulls, zero exact duplicates. Finite/range validation added. Geography, collection period, feature units and field representativeness unresolved.
9. **Models trained:** Decision Tree, Random Forest, scaled KNN, Histogram Gradient Boosting.
10. **Selected model:** Random Forest.
11. **Metrics:** held-out accuracy 0.9955 and macro F1 0.9955; full macro precision/recall/per-class metrics in ml/model_metrics.json.
12. **Cross-validation:** Random Forest five-fold training-split accuracy 0.9943 +/- 0.0051. Full comparison in model_cards.md.
13. **Market integration:** supplied key stored only in ignored .env; API-key placement/query/SSL settings verified in standalone script, but key validity cannot be established without an HTTP response. Nonblocking single background refresh, bounded retry/cooldown, atomic official-response cache and fresh/cached/stale/unavailable statuses. Filter wiring tested with fixtures, not live records.
14. **Price forecasting:** no verified historical observations; unavailable. Existing baseline changed to chronological holdout and minimum 20 observations.
15. **Price metrics:** unavailable; no claimed forecast score from fabricated history.
16. **Disease image classification:** removed from the current application, including model artifacts and the standalone route. Problem Report records symptoms and optional private reference photos only; it does not classify images.
17. **Crop recommendation dataset:** recommendation training continues to use the original `data/Crop_recommendation.csv` file (2,200 rows, 22 labels). Its original source/license/geography remain unverified, and the existing score is not field validation.
18. **Expert groups:** wind/spraying, rainfall/harvest, irrigation/moisture, recent irrigation/fertilizer, humidity/heat, N/P/K. Facts, triggers and conflict explanations displayed. Agronomic thresholds remain unvalidated heuristics.
19. **Activities:** persisted pending/completed/skipped; overdue derived; reschedule returns to pending with new date; owner-scoped updates and duplicate advisory-task prevention.
20. **Action-aware example:** confirmed irrigation within recent interval suppresses repeat irrigation; pending/skipped events do not count as completed. Recent fertilizer suppresses immediate repeat advice.
21. **Fertilizer:** unknown soil inputs do not become invented measurements. Timing/recent-action rules exist; precise references and all alternative-composition claims remain to be validated.
22. **Resources:** community submission/list persistence works; generated catalog excluded. No verified stock or price feed.
23. **Maps:** Leaflet resource map and manual setup. Reverse-geocode endpoint wiring repaired. Browser smoke test checked page JavaScript; GPS permission and every map interaction not manually verified.
24. **Finance:** actual expenses, quantity/unit sales, revenue and net profit repaired/tested. Unsupported benchmark profit estimates disabled. Full crop-cycle accounting and economic simulation remain partial.
25. **Competition:** DeHaat publicly describes crop/weather/input/market services; Plantix publicly describes photo-based crop health and expert community. Claims about their activity memory/integration remain Not Verified. See competitor_analysis.md.
26. **Demonstrated differentiators:** persisted confirmed-action history, activity-sensitive rules, explainable facts, shared FarmState and unified daily plan. No superiority or scientific validation claimed.
27. **Automated result (historical 2026-09-30 run):** `python -m pytest -q --tb=short`.
28. **Passed:** 32 in that historical run.
29. **Failed:** 0 in that historical run. The latest full suite result is 164 passed, 1 warning, 0 failed on 2026-10-15; see `docs/research_audit/TESTING_AUDIT.md`.
30. **Manual end-to-end:** full 61-step manual scenario incomplete. Browser and Flask-client flows cover subsets; blocked market steps cannot be represented as completed.
31. **Browser:** headless Microsoft Edge registration/manual setup with CSRF enabled; 11 page checks including weather, daily/seven-day plans, resources, market, expenses, report and ML analytics; last recorded run had zero page JavaScript exceptions. Mobile dashboard screenshot inspected. No claim of exhaustive control/console/network validation.
32. **Known internal limitations:** economic what-if, feedback workflow, notification event coverage, comprehensive future stage scheduling, multilingual support, independent report exports, exhaustive validation and research comparisons incomplete. Existing legacy services need further consolidation under coverage.
33. **External limitations:** official market-data availability/history, original crop-dataset provenance, and traceable crop cost/yield references. Historical diagnostics disagree on the network stage for data.gov.in; see item 6 and `docs/api_integrations.md`.
34. **Install:** python -m pip install -r requirements.txt.
35. **Train:** python ml/train_model.py.
36. **Run:** python app.py then http://127.0.0.1:5000. Current running session uses existing database and stable local secret.
37. **Test:** python -m pytest -q. Browser: python -m pip install playwright then python scripts/browser_check.py. Standalone network diagnosis: python scripts/diagnose_market_api.py.
38. **Demo sequence:** register, manual farm setup, weather, crop planner, selection and separate sowing confirmation, activities/confirmation, reasoning, symptom report, community resources, expenses/sales, what-if, report, logout/login. Detailed guide: demo_guide.md.
39. **Demo inputs:** use synthetic test account only: 18.5/73.8, N90 P42 K43 pH6.5 T20.8 RH82 rainfall210 moisture24. Do not treat these as actual measured soil/climate.
40. **Unimplemented requirements:** enumerated in requirements_audit.md. Internal engineering gaps are not mislabeled as external blockers. The master document remains the acceptance backlog.

## Market connection evidence

Standalone DNS resolution succeeded. Direct TCP socket raised ConnectionRefusedError, errno 10061. Minimal requests call raised ConnectTimeout. TLS/HTTP/authentication/JSON were not reached. Endpoint, resource ID, query and SSL verification settings are recorded without secrets in artifacts/market_diagnostic.json. No official price sample was obtained.

## Running application

The homepage returned HTTP 200 after restart; the seven-day route redirected an unauthenticated request to /login as expected. A brief restart caused the reported connection-refused browser page; server was verified running afterward.
