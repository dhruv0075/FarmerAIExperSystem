# API integrations

## Integration status

- **Open-Meteo:** `services/weather_service.py` requests modeled current
  conditions and forecasts with an 8-second timeout and a 30-minute
  in-memory cache. If refresh fails, it can return the prior cached payload
  labeled stale. This is provider-model output, not an on-farm sensor
  observation. An earlier project record reports one successful response for
  coordinates 18.5, 73.8 on 2026-09-30; that single historical observation is
  not a current availability guarantee.
- **Nominatim:** `services/location_service.py` attempts reverse geocoding
  with a 5-second timeout and a 24-hour in-memory cache. The service falls
  back to BigDataCloud and then to coordinate text if lookup fails. A prior
  record reports a successful response on 2026-09-30; this was not
  independently rechecked for the current audit.
- **data.gov.in / Agmarknet:** resource
  `9ef84268-d588-465a-a308-a864a43d0070`. `DATA_GOV_IN_API_KEY` is read from
  the process environment. The adapter validates returned records, caches
  successful results and does not use generated market fixtures. It requests
  at most 10 records per query; this is not complete nationwide pagination.
  A historical diagnostic record documents DNS/TCP/TLS success followed by a
  timeout while awaiting the HTTP response. Another older handover reports a
  TCP failure before TLS. These diagnostic records conflict, and neither is
  current evidence. Key acceptance, response format and usable live price
  records remain **unverified**. Do not infer live integration success or
  failure stage from these old observations.
- **Leaflet/OpenStreetMap tiles and Bootstrap/Chart.js assets:** the
  applicable pages may require CDN/network access. Text listings remain
  usable when map assets fail to load.

Do not paste credentials into reports or source control. `.env` is ignored.

## Market API configuration

For local development, copy `.env.example` to `.env` and set
`DATA_GOV_IN_API_KEY`, or configure it in the process environment. For
production, set it through the host's secret environment-variable mechanism.
Never put the key in source, committed configuration, request logs, URLs
shared publicly, or chat. `.env` and `.env.*` are ignored by Git; `.env.example`
contains only a blank placeholder.

If the portal requires a key for this resource, use the data.gov.in account's
API/access section to obtain one and follow its current instructions. The
historical timeout did not receive an HTTP response and therefore does not
prove whether the resource accepts unauthenticated requests or whether any
configured key is valid.

Run `python scripts/diagnose_market_api.py` only when a new bounded live
diagnostic is intended. It checks DNS/TCP/TLS and makes a small provider
request; it writes sanitized stages to the ignored
`artifacts/market_diagnostic.json`, does not write raw records or print a key,
and retains SSL verification. A failure before HTTP means authentication,
JSON parsing and usable-record count remain unverified.

## Market refresh behavior

The official adapter has a process-local lock, bounded retries, cooldowns,
cache and atomic cache-file replacement. The current source sets three
attempts with 0.5/1-second retry delays, a five-minute failure cooldown,
30-minute per-query success cache, and five-second spacing for new filtered
queries. It does not refresh at app startup; explicit refresh actions make
the request. Cache records retain source and original fetch time.

The market refresh lock and in-memory state are local to one process. They are
not distributed across workers or serverless instances; see
[`deployment.md`](deployment.md) and [`vercel.md`](vercel.md). The 10-record
query limit also means repeat refreshes do not guarantee a complete or
sufficiently long market history for price forecasting.
