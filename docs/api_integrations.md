# API integrations

- Open-Meteo: https://open-meteo.com/en/docs ? live request verified at 18.5,73.8 on 2026-09-30; ten forecast days returned. 30-minute memory cache; stale actual observations only. Weather page persists full payload for restart fallback.
- Nominatim: https://nominatim.openstreetmap.org/reverse ? live address response verified for the same coordinates. Coordinate-only fallback when unavailable; manual location remains usable.
- data.gov.in: https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi ? resource 9ef84268-d588-465a-a308-a864a43d0070. DATA_GOV_IN_API_KEY loaded from ignored .env or environment. Endpoint resolved to an address but HTTPS connection timed out after 15 seconds during verification; authentication therefore unverified. Adapter validates dates/prices, preserves market/variety identity, caches successful results, and never reads generated price fixtures. The adapter first requests a 10-row unfiltered sample, then 10-row commodity/state/district/market filters. Nationwide pagination remains incomplete.
- Leaflet/OpenStreetMap tiles and Bootstrap/Chart.js assets require CDN/network availability. Resource text listings remain visible if map code cannot load.

Do not paste credentials into reports or source control. .env is ignored.

## Standalone diagnosis and refresh lifecycle

DNS succeeds. Direct TCP probe raised ConnectionRefusedError (WinError 10061); requests raised ConnectTimeout. TLS, HTTP response, authentication and JSON parsing were not reached. See artifacts/market_diagnostic.json. SSL verification stays enabled; key stays in api-key query parameter, never logs.

One process-wide lock/in-flight state suppresses duplicate concurrent refreshes. Three attempts with 0.5/1 second delays, five-minute failure cooldown, 30-minute per-query successful cache and five-second global successful-query spacing. No refresh occurs at startup. Page loads return immediately. Cache persisted atomically with original source and fetch timestamp. Fresh/cached/stale/unavailable and refresh-in-progress are exposed on market page.
