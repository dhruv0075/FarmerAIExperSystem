# Feature Audit v2

Date: 2026-10-03. Classification reflects current implementation and executed baseline checks, not intended functionality. Navigation visibility is recorded separately from route availability.

## Farmer and public product

| Feature / route | Classification | User-visible status and evidence | Product action |
|---|---|---|---|
| Home `/` | PARTIAL | Loads; conveys decision-support scope, but current image-led Bootstrap layout lacks a distinctive product hierarchy and has no interactive visualization. | Redesign as focused product hero; retain clear CTA and honest workflow. |
| About `/about` | PARTIAL | Static project overview; overlaps Research / AI Details. | Keep route for context; remove duplicate prominence from primary navigation. |
| Registration `/register` | WORKING | Email normalization, generic duplicate/invalid response, password rules/hash, CSRF; black-box cases pass. | Preserve behavior; polish form presentation. |
| Login `/login` | WORKING | Generic failure message; permanent session; account-bound session token. | Preserve security and improve visual continuity. |
| Logout `/logout` | WORKING | POST+CSRF only; clears cookie; browser Back/direct dashboard checked. | Preserve. |
| Dashboard `/dashboard` | PARTIAL | Data is sourced from farm, current plan, forecast, activities, lifecycle, advisories; black-box/browser route passes. Information hierarchy remains weak compared with the core promise. | Redesign around primary action, evidence, crop/weather and concise outlook. |
| Farm setup `/farm/setup` | WORKING | Manual location and form save passed browser workflow; area and coordinate boundaries pass; browser geolocation denial falls back to manual. | Preserve; polish steps and maintain fallback. |
| Farm profile `/farm` | WORKING | Authenticated page GET tested; ownership is scoped to current farmer. | Retain as My Farm. |
| Location / reverse geocode `/api/location`, `/api/reverse-geocode` | PARTIAL | Manual coordinates and denial fallback are exercised; successful GPS grant/reverse-geocode browser flow is not part of baseline. | Keep optional; improve status presentation without requiring GPS. |
| Soil snapshot | PARTIAL | Crop planner validates NPK, pH, humidity, rainfall, moisture and persists successful recommendation input; setup baseline soil values remain optional. | Retain, distinguish measured from farmer-entered values. |
| Crop Planner `/crop-recommendation` | WORKING | Saved classifier produced a crop, model confidence and alternatives in browser; invalid input and missing-model failure covered. Dataset provenance/generalization remain uncertain. | Retain as the primary ML feature; improve guidance/output hierarchy. |
| Recommendation selection `/recommendations/<id>/select` | WORKING | Browser selected a predicted crop and entered lifecycle; ownership checks are present. | Preserve. |
| Weather `/weather`, `/api/weather` | WORKING | Live Open-Meteo returned available data in local browser; timeout/cache parsing covered in tests. | Retain; label data source/availability clearly. |
| Crop Lifecycle `/lifecycle` | PARTIAL | Start/date validation and current-stage estimates work; accessible timeline exists, but stage progression lacks a strong visual anchor. | Keep accessible stage timeline and add optional crop visualization. |
| Daily Farm Plan `/daily-plan` | PARTIAL | DO FIRST/TODAY/WATCH/AVOID/UPCOMING logic and activity/weather conflicts exist; exact full irrigation decision table is not tested. | Retain as the main daily action view; clarify evidence and visual urgency. |
| Seven-day plan `/seven-day-plan` | PARTIAL | Route renders and has generated weather/action plan; all market/day scenarios not independently verified. | Retain as a compact outlook, not a chart-heavy dashboard. |
| Activities `/activities` | WORKING | Browser created pending item, completed with note, reloaded, and left another pending; tests cover skipped, rescheduled and overdue. | Preserve and surface confirmation state consistently. |
| Advisories `/advisories`, `/advisories/generate` | PARTIAL | Rules and saved activity integration exist; all rule combinations and agronomic thresholds are not field-validated. | Keep advice transparent and avoid definitive agronomic claims. |
| Disease detection `/disease-detection` | PARTIAL | Separate upload-and-screen page runs the 38-class PlantVillage model; top class is an unverified suggestion, images are not saved, and full dataset browsing links to Hugging Face. | Keep suggestions non-diagnostic; obtain independent labeled calibration and held-out datasets before treating class results as reliable. |
| Problem report `/report-problem` | WORKING | Saves farmer symptoms and optional private reference photos without model inference. | Keep symptom reporting separate from image screening. |
| Private report image `/disease-image/<id>` | WORKING | Owner check and private storage; unauthorized/missing-ID tests pass. | Preserve. |
| Report result `/disease-result/<id>` | PARTIAL | Displays symptoms, private reference image, and safe field checks; it does not display disease-model output. | Preserve separation; direct image screening to `/disease-detection`. |
| Market `/market`, `/market/refresh` | BLOCKED_EXTERNAL / PARTIAL | UI remains available and cache states are tested; live provider DNS succeeds but TCP connection is refused before HTTP/auth. No live price verified. | Keep optional with graceful unavailable state; never fabricate prices. |
| History `/history` | PARTIAL | Recommendations, cycles and advisories are scoped to current farmer; cross-user page test passes. Complete activity/report timestamp coverage is not exhaustive. | Retain; present concise chronological history. |
| Settings `/settings` | WORKING | Profile update and password-change flow exist; disabled translation selector was removed. | Retain; strengthen hierarchy and retain security copy. |
| Notifications `/notifications` | PARTIAL | Read/mark-all routes and topbar link work; event-generation coverage is incomplete. | Keep access, avoid claiming comprehensive notifications. |
| Research / AI Details `/research` | WORKING | Consolidates ML metrics, sources, reasoning and limitations; available via core navigation. | Retain technical detail here rather than on farmer daily views. |
| Data transparency `/data-transparency` | PARTIAL / DUPLICATE | Separate transparency route overlaps Research / AI Details. | Keep route if directly linked, remove duplicate primary navigation. |
| Health `/healthz` | WORKING | Public health response 200; serverless import guard passes. | Retain for deployment health checks. |

## Legacy and specialist routes

| Feature / route | Classification | Current visibility/status | Product action |
|---|---|---|---|
| Expert system `/expert-system` | HIDDEN / PARTIAL | Technical IF-THEN trace page; not a primary navigation item. Rule thresholds require domain validation. | Keep details in Research; leave legacy route for existing links. |
| Fertilizer `/fertilizer` | HIDDEN / PARTIAL | Specialist advice route; detailed agronomic source validation incomplete. | Do not promote as primary navigation. |
| Resources `/resources`, `/add-resource` | HIDDEN / PARTIAL | Community/resource directory and submissions exist; live inventory/price verification unavailable. | Keep route/data; do not imply verified stock. |
| Crop comparison `/compare-crops` | HIDDEN / PARTIAL | Comparison workflow exists but is not promoted as core. | Keep behind planner/research context if needed. |
| ML analytics `/ml-analytics` | HIDDEN / WORKING | Technical model metrics route. | Consolidate access through Research / AI Details. |
| Risk analysis `/risk-analysis` | HIDDEN / PARTIAL | Heuristic risk factors; no independent scientific validation. | Do not promote as an independently validated score. |
| Profit planner `/profit-planner` | HIDDEN / PLACEHOLDER | Unsupported profit benchmarks were removed; verified inputs are insufficient for reliable projection. | Keep out of core navigation. |
| Sell planner `/sell-planner` | HIDDEN / BLOCKED_EXTERNAL | Requires live market/location/economic context not verified. | Keep out of core navigation until data is available. |
| What-if `/what-if` | HIDDEN / PARTIAL | Non-mutating agronomic scenarios exist; economic simulation is incomplete. | Keep out of core navigation. |
| Expenses `/expenses`, `/add-expense`, `/add-sale` | HIDDEN / ACTIVITY-LINKED | Costs are recorded from completed activities; the legacy `/add-expense` POST redirects to Activities without writing. Sales remain separately recordable. | Use activity completion for expenses; keep totals/history available outside main nav. |
| Farm report `/report` | HIDDEN / PARTIAL | Existing printable report route; full report types/export pipeline not complete. | Keep route; do not promise export formats not present. |
| Disease AI | PLACEHOLDER / intentionally unavailable | No validated image model is installed; no active diagnosis claim should be shown. | Do not expose as AI diagnosis. |
| Price forecasting | PLACEHOLDER / BLOCKED_EXTERNAL | No verified sufficient historical price observations. | No fabricated forecast or confidence. |
| Error/404/500 pages | WORKING | Friendly templates; black-box invalid URL and simulated model failure are covered. | Preserve; ensure never display tracebacks. |

## Shared UI and deployment

| Area | Classification | Current observation | Product action |
|---|---|---|---|
| Shared visual system | PARTIAL | CSS variables and responsive shell exist, but pages still inherit Bootstrap components and inconsistent density. | Extend existing CSS tokens/components; do not replace Flask/Jinja architecture. |
| Navigation | WORKING / PARTIAL | Core sidebar and clickable destinations pass browser check; active-state and information hierarchy can be improved. | Preserve routes, improve selection and mobile behavior. |
| Authentication/security | WORKING | 116-test baseline includes auth, CSRF, cookie, ownership, stale-session and upload checks. | Do not weaken; rerun after UI changes. |
| Vercel writable paths | WORKING with limitation | Production import and repository-write guard pass; storage is per-instance `/tmp`. | Preserve path contract; document ephemeral persistence. |
| External assets | PARTIAL | Fonts, Bootstrap, icons and map libraries use CDNs; final baseline browser had no failed resources. | Keep optional 3D lazy-loaded with static fallback; test failure path. |

## Summary

- Core ML/weather/activity/report flows are WORKING at the boundaries tested.
- Home, dashboard, lifecycle and shared UI are PARTIAL primarily because of presentation and limited interaction coverage; this phase targets those without altering route contracts.
- Market access is BLOCKED_EXTERNAL in this environment. Disease inference and unsupported price/profit estimates remain intentionally unavailable.
- Specialist pages remain accessible as legacy routes but are HIDDEN from primary navigation.
