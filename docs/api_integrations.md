# API integrations

- Open-Meteo: https://open-meteo.com/en/docs ? live request verified at 18.5,73.8 on 2026-09-30; ten forecast days returned. 30-minute memory cache; stale actual observations only. Weather page persists full payload for restart fallback.
- Nominatim: https://nominatim.openstreetmap.org/reverse ? live address response verified for the same coordinates. Coordinate-only fallback when unavailable; manual location remains usable.
- data.gov.in: https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi ? resource 9ef84268-d588-465a-a308-a864a43d0070. `DATA_GOV_IN_API_KEY` is loaded from ignored `.env` or the process environment. A single live diagnostic request on 2026-09-30 resolved DNS, connected over TCP, and completed TLS 1.3, but timed out waiting for the HTTP response. The key's acceptance, response format, and usable records are therefore **unverified**; this is not evidence of a successful live integration. The adapter validates dates/prices, preserves market/variety identity, caches successful results, and never reads generated price fixtures. The adapter requests a 10-row sample; it does not paginate a complete nationwide dataset.
- Leaflet/OpenStreetMap tiles and Bootstrap/Chart.js assets require CDN/network availability. Resource text listings remain visible if map code cannot load.

Do not paste credentials into reports or source control. .env is ignored.

## Standalone diagnosis and refresh lifecycle

For local development, copy `.env.example` to `.env` and set `DATA_GOV_IN_API_KEY` there, or set that variable in the shell before starting the app. Keep the key private; `.env` and `.env.*` are ignored by Git, while `.env.example` contains only a blank placeholder. For production, add `DATA_GOV_IN_API_KEY` as a secret environment variable in the hosting provider (for example, Render's service environment or Vercel's project environment variables); never put the key in source, committed configuration, URLs, or chat.

If the data.gov.in portal requires a key for the resource, sign in to your data.gov.in account, open the resource's API/access section, and use the account's API-key management flow to generate or view your own key. Follow the portal's current instructions if labels differ; do not share the key. The current timeout did not reach an HTTP response, so it does **not** establish whether this resource accepts unauthenticated requests or whether the configured key is valid.

Run `python scripts/diagnose_market_api.py` for one bounded API request plus DNS/TCP/TLS checks. The diagnostic reports whether a key is configured, HTTP/authentication/JSON stages and usable-record counts when reached. It writes only sanitized stage results to the ignored `artifacts/market_diagnostic.json`; it never writes raw provider records or prints the key. A timeout means later stages are reported as unverified. SSL verification stays enabled and the key is never logged.

One process-wide lock/in-flight state suppresses duplicate concurrent refreshes. Three attempts with 0.5/1 second delays, five-minute failure cooldown, 30-minute per-query successful cache and five-second global successful-query spacing. No refresh occurs at startup. Page loads return immediately. Cache persisted atomically with original source and fetch timestamp. Fresh/cached/stale/unavailable and refresh-in-progress are exposed on market page.
