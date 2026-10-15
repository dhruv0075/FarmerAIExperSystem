# AgriWise AI Black-Box Test Report

Date: 2026-10-02
Scope: Existing local Flask application, local Edge browser workflow, and unauthenticated public deployment checks. No credentials or production farmer data were used.

## Test Results

| Test ID | Module | Technique | Scenario | Input | Expected Result | Actual Result | Status | Severity | Fix Applied | Retest Result |
|---|---|---|---|---|---|---|---|---|---|---|
| BB-001–008 | Registration | Equivalence partitions | Empty name/email/password, invalid email, weak/short/long password, letters-only, digits-only | Invalid combinations from parametrized test | Generic validation response; no account or traceback | Generic message; zero users persisted | PASS | LOW | None | Passed in final matrix |
| BB-009 | Registration/login | Equivalence + state | Trim and normalize email; case-insensitive duplicate; uppercase login | Whitespace and mixed-case email variants | One account; generic duplicate response; normalized login works | Observed as expected | PASS | LOW | None | Passed in final matrix |
| BB-010 | Registration/dashboard | Error guessing / XSS | Script-shaped name displayed after registration | `<script>alert(1)</script>` | Render as text, never execute | Escaped HTML; browser did not execute it | PASS | MEDIUM | None | Passed in final matrix |
| BB-011–012 | Password policy | Boundary values | Minimum and maximum accepted password lengths | 8 and 128 characters | Both accepted | Both registered successfully | PASS | LOW | None | Passed in final matrix |
| BB-013–016 | Login | Equivalence partitions | Wrong password, unknown email, empty email/password | Four invalid credential combinations | Same generic login error; no protected session | Generic error; login did not succeed | PASS | MEDIUM | None | Passed in final matrix |
| BB-017–023 | Password change | Decision table / negative | Wrong current password; short, overlong, letters-only, digits-only, mismatch, same as old | Seven invalid combinations | Reject change; existing credential remains valid | All rejected; old password still logged in | PASS | MEDIUM | None | Passed in final matrix |
| BB-024–027 | Farm setup | Boundary values | Area zero, negative, minimum positive, normal positive | 0, -0.1, 0.1, 2.5 | Accept positive area only | 0 and negative rejected; positive values saved | PASS | MEDIUM | None | Passed in final matrix |
| BB-028 | Farm setup | Error guessing / boundary | Empty farm name and very large finite area | Empty name; area 1e100 | Empty name rejected; positive finite area does not crash | Empty name rejected; 1e100 accepted and stored; no upper limit is defined in the current form contract | PASS | LOW | None | Passed; large-area behavior noted |
| BB-029–032 | Farm location | Boundary values | Coordinate endpoints and normal location | Latitude -90/90, longitude -180/180, 0/0, 18.5/73.8 | Accept in-range coordinates | Saved successfully | PASS | MEDIUM | None | Passed in final matrix |
| BB-033–036 | Farm location | Boundary values | Coordinates just outside allowed range | -90.1, 90.1, -180.1, 180.1 | Reject with useful validation; no farm saved | Rejected; no farm persisted | PASS | MEDIUM | None | Passed in final matrix |
| BB-037–048 | Crop planner | Boundary values | Zero nutrients/rainfall; pH 0/7/14; humidity 0/50/100; temperature -10/50; valid positive input | 12 complete valid combinations | Real model result; confidence shown only when returned by model | Prediction result and confidence rendered; recommendation saved | PASS | HIGH | None | Passed in final matrix and browser journey |
| BB-049–059 | Crop planner | Negative / boundary | Negative NPK/rainfall; pH/humidity/moisture out of range; NaN/Infinity; missing field | 11 invalid combinations | Validation message; no recommendation persisted | Rejected with validation message; no recommendation saved | PASS | MEDIUM | None | Passed in final matrix |
| BB-060 | Crop planner | Negative | Missing required crop input | Nitrogen only | Reject request; do not save soil/recommendation | Rejected; no soil row saved | PASS | MEDIUM | None | Passed in final matrix |
| BB-061 | Crop planner | Error guessing / failure injection | Model unavailable after valid form submission | Simulated `FileNotFoundError` | Graceful unavailable response; no partial write or traceback | Initial result was HTTP 500; fixed to HTTP 503 with user message and no soil snapshot | PASS | HIGH | Catch prediction failure before persistence; return temporary-unavailable state | Exact scenario retested PASS |
| BB-062 | Weather | Negative / external API | No farm coordinates and provider timeout | Missing coordinates; simulated timeout | Clear unavailable/error response; no crash | No-coordinates response is 400 with guidance; timeout returns JSON failure | PASS | HIGH | None | Passed in final matrix |
| BB-063 | Lifecycle | State transition | Start on today's date; submit future date | Today and tomorrow | Today starts; future date rejected without a cycle | Today starts; future date redirects with validation flash and creates no cycle | PASS | MEDIUM | No application fix; corrected test expectation from HTTP 400 to redirect-plus-message | Retested PASS |
| BB-064 | Lifecycle | Boundary / equivalence | Old date and unsupported crop | Date 10 years ago; unknown crop | Supported historical cycle accepted; unsupported crop rejected | Old date accepted; unsupported crop rejected; only valid cycle saved | PASS | MEDIUM | None | Passed in final matrix |
| BB-065 | Problem report | XSS / negative upload | Script markup in symptoms/notes; fake image bytes named `.jpg` | `<script>` / `<img onerror>` and invalid image | Text escaped; fake image rejected; symptom report remains safe | Markup escaped; fake image HTTP 400; no extra report | PASS | HIGH | None | Passed in final matrix |
| BB-066 | Problem report upload | Error guessing / path traversal / size | Valid image with traversal-style name; image larger than limit | `../../outside.png`; 5 MiB + 1 byte | Store under generated private name; reject oversize | Traversal normalized to private filename; oversize HTTP 413 | PASS | HIGH | None | Passed in final matrix |
| BB-067 | Problem report upload | Boundary value | Valid image exactly at advertised 5 MiB limit | 5 MiB file plus multipart body | Accept at limit | Initial result HTTP 413 because request cap included multipart overhead; fixed and accepted | PASS | MEDIUM | Allow bounded multipart overhead; retain explicit 5 MiB file-size check | Exact scenario retested PASS |
| BB-068 | Problem report upload | Negative | Executable/non-image extension | `.exe`, `application/octet-stream` | Reject; no report saved | HTTP 400; no report saved | PASS | HIGH | None | Passed in final matrix |
| BB-069 | Routing/auth | Error guessing / security-visible | Unknown URL and protected crop route without session | Invalid path; `/crop-recommendation` | Clean 404; protected route redirects to login | HTTP 404 and 302 to `/login`; no traceback | PASS | HIGH | None | Passed locally and live unauthenticated check |
| BB-070 | Private image | Error guessing | Nonexistent report image ID | ID 999999 | Clean not-found response | HTTP 404; no traceback | PASS | MEDIUM | None | Passed in final matrix |
| BB-071 | User isolation | ID tampering / negative | Farmer B requests dashboard/history/activity/problem pages after Farmer A creates unique records | Two accounts and distinct farm/activity/symptom markers | B sees own records only | B saw own farm; A's farm, activity, and symptom markers absent | PASS | CRITICAL | None | Passed in final matrix |

## Additional Executed Checks

| Check | Technique | Actual Result | Status |
|---|---|---|---|
| Existing project regression suite | End-to-end, domain, security, integration | `python -m pytest -q`: 116 passed | PASS |
| Dedicated black-box matrix | Equivalence partitions, boundary values, negative/failure cases | `python -m pytest tests/test_black_box.py -q`: 71 passed | PASS |
| Local Edge journey | Registration, manual location, setup, 12 core routes, clickable sidebar, notification, daily/seven-day CTA | All checked routes returned HTTP 200 | PASS |
| Crop journey | Live weather API, weather autofill UI, model prediction, crop selection, lifecycle start | Open-Meteo returned available data; prediction and lifecycle completed | PASS |
| Activity journey | Create pending, complete with note, reload, leave second task pending | Status and farmer note persisted; pending task remained pending | PASS |
| Problem report journey | Upload valid PNG and open report result | Automated checks run the supplied checkpoint through the authenticated report route, persist the image and uncertain result, and suppress the raw disease label. | PASS (automated); disease accuracy NOT MEASURED |
| Account journey | Change password, login with new password, logout, browser Back, direct dashboard, login again | Protected access redirected to login after logout; no private sidebar restored | PASS |
| Responsive browser checks | Desktop 1366 px, tablet 768 px, mobile 390 px | No horizontal overflow; mobile sidebar toggle and dashboard assertions passed | PASS |
| Browser console/resource scan | Page errors, failed requests, HTTP errors | Final run: 0 JavaScript errors, 0 failed requests, 0 HTTP errors | PASS |
| Production-mode import | `AGRIWISE_ENV=production`, isolated data path and test secret | App imported; Secure cookie true; serverless repository-write guard passed | PASS |
| Live deployed public checks | HTTP health, root, protected crop URL, invalid route | `/healthz` 200, `/` 200, protected crop redirects 302 to `/login`, invalid route 404 | PASS |
| Live official market provider | DNS/TCP staged diagnostic | DNS succeeded; TCP refused with `ConnectionRefusedError` 10061; HTTP/auth not reached | BLOCKED: external network |

## Initial Failures and Fixes

- First 53-case black-box run: 51 passed and 2 failed. Missing crop-model handling returned 500 (HIGH defect). The future lifecycle test expected status 400, while actual user-facing behavior was a redirect with a validation message and no cycle write; the test expectation was corrected, not application behavior.
- Exact 5 MiB image boundary test initially returned 413 because Flask's whole-request limit also counted multipart overhead (MEDIUM defect). The request cap now allows bounded multipart overhead while a separate file-size check still enforces 5 MiB.
- Retests for both reproduced application defects passed. Final dedicated suite: 71 passed, 0 failed. Final full suite: 116 passed, 0 failed.
- One intermediate browser run observed a Bootstrap CDN request cancelled during navigation (`ERR_ABORTED`); it did not recur. Final browser run had no failed requests or HTTP errors.

## Test Summary

| Measure | Result |
|---|---:|
| Total black-box test cases | 71 |
| Passed initially | 51 of the initial 53-case run |
| Failed initially | 2 (one application defect; one incorrect expected status code) |
| Defects found | 2 application defects |
| Critical defects | 0 |
| High defects | 1 |
| Medium defects | 1 |
| Low defects | 0 |
| Defects fixed | 2 |
| Retests passed | 71 |
| Final passed | 71 |
| Final failed | 0 |
| Full project suite | 116 passed, 0 failed |
| Remaining reproducible defects in executed cases | 0 |

## Not Fully Executed / Limitations

- Authenticated production Vercel UI testing was NOT EXECUTED: the shared browser had no farmer session. Production checks covered public health, home, expected protected-route redirect, and 404 behavior only.
- Successful official market API access was NOT EXECUTED because the local environment's TCP connection was refused before HTTP/authentication. UI outage/cache behavior is exercised with test fixtures; no live price was verified.
- A complete 8-row irrigation decision truth table was NOT EXECUTED. Existing tests cover completed irrigation suppression, pending/skipped not-as-completed semantics, and heavy-rain conflict avoidance, but not every combination of recent irrigation × heavy rain × low moisture.
- Explicit browser geolocation grant was NOT EXECUTED. The browser exercised detect-location failure/denial fallback to manual map, and manual coordinates were submitted successfully.
- Browser checks did not click every control on every page. They covered main navigation, topbar notifications, dashboard plan links, crop selection, weather autofill, activity create/complete, report upload, password change, logout and responsive sidebar.
- Cross-account content isolation was tested for dashboard, history, activity and problem-report pages, plus activity ID and private image/report ID access in the existing integrity suite. Every possible object ID route (including finance/advisory/crop-cycle permutations) was NOT EXECUTED.
- No explicit maximum farm area is defined; a finite area of `1e100` is accepted. Current documented validation requires area greater than zero, so this was recorded as behavior, not a failure against a defined maximum.
- Vercel `/tmp` remains ephemeral and per-instance. Live deployment durability, cross-instance database sharing, provider networking from Vercel, and authenticated multi-instance behavior are NOT EXECUTED.

## Readiness

- Demo readiness: YES for a local/demo environment using synthetic farmer data. The crop classifier, core journey, activity confirmations and honest problem-report flow were exercised. Market pricing must be described as unavailable when the official source cannot be reached.
- Production-style readiness: NO. Remaining blockers include ephemeral per-instance SQLite/uploads on Vercel, no shared durable session/account store or rate limiter, no email password-reset provider, blocked market API connectivity from this environment, and no independent field validation of the crop dataset.

Commands executed:

```powershell
python -m pytest tests/test_black_box.py -q
python -m pytest -q
python scripts/browser_check.py
python scripts/verify_serverless.py
python scripts/diagnose_market_api.py
```
