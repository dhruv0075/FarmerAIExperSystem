# Current Baseline

Date: 2026-10-03
Baseline is captured before UI/product changes in this work phase. The worktree already included the earlier authentication/session fixes and the crop-model and upload-boundary fixes.

## Automated Checks

| Check | Result | Notes |
|---|---|---|
| `python -m pytest tests/test_black_box.py -q` | PASS: 71 passed | Completed in 42.45 seconds. |
| `python -m pytest -q` | PASS: 116 passed | Completed in 56.93 seconds. |
| `python scripts/verify_serverless.py` | PASS | Ran with disposable `AGRIWISE_DATA_DIR`, production mode, test-only secret and bytecode disabled. Repository write guard passed. |
| Production app import | PASS | `APP IMPORT SUCCESS`; `SESSION_COOKIE_SECURE=True`. |

## Browser Baseline

The first Edge attempt timed out loading `/register` while both pytest suites were running concurrently. It was rerun alone and passed.

- Registration, manual location, farm setup, dashboard, crop planner, lifecycle, report, activity, password, and session journey completed.
- 12 core routes returned HTTP 200; sidebar, topbar notification, dashboard plan links and combined crop/weather/lifecycle/report/activity flows passed.
- Open-Meteo returned `available` from the local authenticated test journey.
- Responsive checks: desktop 1366 px, tablet 768 px, mobile 390 px.
- Final retry: 0 JavaScript exceptions, 0 failed browser requests, 0 HTTP errors.
- No broken routes in the tested local browser set.

## Environment Limits

- The public Vercel deployment was not exercised with an authenticated farmer session; only local authenticated browser flows were run.
- This baseline run does not establish durable Vercel persistence. Runtime storage remains `/tmp` and per-instance.
- The live official market API was not tested during this baseline run; market behavior is optional and has existing cache/failure tests.
- Third-party browser assets depend on external CDNs; no CDN request failed on the successful baseline browser run.

## Baseline Summary

- Black-box suite: 71 passed, 0 failed.
- Full suite: 116 passed, 0 failed.
- Browser workflow: passed on retry; initial concurrent-run timeout recorded above.
- Serverless verification: passed.
- Changes made during this baseline step: documentation only.
