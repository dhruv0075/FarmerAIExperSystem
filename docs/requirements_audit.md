# AgriWise acceptance audit ? 2026-09-30

This is an existing-project repair, not a replacement architecture. COMPLETE below means the stated bounded behavior is exercised; it does not mean every master requirement is complete.

| Master sections | Status | Evidence / remaining gap |
|---|---|---|
| 4, 8?11 | COMPLETE | Flask/SQLite preserved; existing DB inspected; registration/login/protected setup tested. |
| 5?7 | PARTIAL | Source-based competitor comparison; no empirical comparative user study. |
| 12?16 | PARTIAL | Browser manual setup tested; reverse geocoding endpoint fixed and live-tested; soil opt-out respected. GPS permission/denial and every wizard branch not yet browser-tested. |
| 17?23 | PARTIAL | FarmState, orchestrator, daily/seven-day pages, risk/index and conflict rules exist. Missing observations now excluded from index. All modules are not fully synchronized; stage-specific future scheduling remains basic. |
| 24?29 | PARTIAL | 2200-row local dataset audited, four models trained and evaluated; original provider/license/collection geography and period unverified. ML metrics are local evaluation only. |
| 30?33 | PARTIAL | ML probability, dataset fit and multi-factor ranking exist; heuristic crop knowledge lacks exact source references. Missing-input ML declines instead of guessing; reduced-data ranking is incomplete. |
| 34?38 | PARTIAL | Live Open-Meteo 10-day response verified; cache/outage tests; current precipitation no longer substituted for model rainfall. Weather-unit and agronomic validation remain research limitations. |
| 39?42 | BLOCKED BY EXTERNAL DATA/API | Supplied key configured locally; api.data.gov.in resolves but HTTPS connection timed out before authentication. No verified market observations available. Generated prices excluded. Historical forecast unavailable; code requires 20 observations and chronological holdout. |
| 43?45 | PARTIAL | Comparison and actual financial calculations work. Profit estimates disabled where yield/cost references are unverified. Economic what-if/comparison incomplete. |
| 46?54 | PARTIAL | Selection requires separate lifecycle confirmation; activity create/complete/skip/reschedule/overdue and isolation tested. Advisory task duplicates prevented. Detailed urgency/evidence and all lifecycle boundaries not fully verified. |
| 55?59 | PARTIAL | Daily/seven-day plans and recent-action suppression; no automatic day-3/day-6 irrigation. Nutrient unknown state implemented. Fertilizer knowledge needs reference validation before real-world application. |
| 60?64 | BLOCKED BY EXTERNAL DATA/API | Symptom reporting and validated image upload work. No legitimate trained disease model/data/evaluation exists in repository. Manual review fallback; fabricated diagnostic probabilities removed from active flow. |
| 65 | PARTIAL | Heuristic risk dimensions and unknown states; index not scientifically validated. |
| 66?70 | PARTIAL | Leaflet/community directory and submission persistence; generated vendor catalog excluded. Stock/prices unknown. No trusted real-time vendor inventory integration. |
| 71?73 | BLOCKED BY EXTERNAL DATA/API | Price adapter exists; market coordinates/history absent. Transport-aware net opportunity cannot be calculated honestly without these inputs. Sell planner UI remains partial. |
| 74?75 | COMPLETE | Existing expense/sales schema repaired; actual HTML fields, dates, quantities and financial persistence tested. Receipts/cycle allocation remain partial. |
| 76 | PARTIAL | Agronomic what-if is non-mutating; economic scenario simulation missing. |
| 77 | PARTIAL | Notifications storage/read routes exist; comprehensive event-generation coverage missing. |
| 78 | MISSING | Feedback table exists but complete feedback submission/research workflow not implemented. |
| 79?87 | PARTIAL | Rule facts/traces, ML analytics and transparency pages. Disease/market metrics correctly unavailable. Agronomic source validation remains incomplete. |
| 88?90 | PARTIAL | Existing responsive UI preserved; Edge desktop/mobile smoke checks. Full multilingual infrastructure and complete interaction audit missing. |
| 91?97 | PARTIAL | 24 domain tables, foreign keys/indexes; additive legacy migration with backup; secure random secret, CSRF, private image authorization, image validation. Exhaustive malformed-input coverage remains incomplete. |
| 98?105 | PARTIAL | Unified printable report and documentation; separate report types/PDF pipeline and field research evaluation incomplete. |
| 106?125 | PARTIAL | Existing and additional regression tests plus headless Edge smoke test. Not all listed acceptance cases have tests. |
| 126 | PARTIAL | Registration/manual farm setup through dashboard browser-tested; crop/activity/finance/problem flows tested with Flask client. Full 61-step manual journey not completed, particularly market/image-model steps. |
| 127?137 | PARTIAL | Targeted failures repaired and regression run; unavailable data explicitly identified. Product must not be declared fully compliant with master document. |

## Initially BROKEN, repaired
Crop alias selection; advisory farm foreign key; history route; expense/sale/report column mismatches; disease prediction persistence; fertilizer/seven-day template contracts; initial reverse-geocoding endpoint; resource submission/list contract; resource JavaScript; legacy weather/advisory schema; weather persistence; fabricated offline weather and generated market/vendor data; missing-data risk labeling; automatic lifecycle start; fake disease confidence; form CSRF; image validation/access.

## Preservation
No farmer rows deleted or reset. Before additive legacy schema repair, SQLite backup saved under artifacts/database_before_schema_repair.db. Original model files saved under artifacts/original_models. Generated source fixtures remain on disk but are excluded from live market/resource paths.
