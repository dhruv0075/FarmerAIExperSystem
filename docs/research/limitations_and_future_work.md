# Limitations and future work

Every item below is a real limitation of the current system or a genuine
blocker. None is softened.

## Scientific and data limitations

1. **Dataset provenance unresolved.** Provider, licence, collection geography
   and collection period for `data/Crop_recommendation.csv` are unknown. No
   regional or national accuracy claim is defensible.
2. **No geographic validation.** Rows are split at random. Rows from the same
   region or batch can appear in both train and test.
3. **No temporal validation.** No train-on-past/test-on-future split exists.
4. **Near-duplicate leakage not measured.** Zero *exact* duplicates were found;
   near-duplicates in feature space were not tested. In a perfectly balanced
   100-per-class dataset this is a real risk.
5. **Class pooling.** 22 agronomically heterogeneous classes share one
   classifier. L2 in `literature_review.md` explicitly recommends against
   pooling crop categories.
6. **Class balance is artificial.** Exactly 100 rows per class is a property of
   construction. Deployment priors will differ.
7. **N/P/K units unstated.** Farmer laboratory reports may not be comparable to
   training features.
8. **Agronomic rules are unvalidated heuristics.** `crop_knowledge.json` lacks
   traceable agronomic references. Fertilizer and application guidance must not
   be treated as prescriptive.
9. **Crop knowledge is hand-configured**, not derived from labelled data.

## External dependency limitations

10. **Official market API unverified live.** The data.gov.in adapter is
    implemented and unit-tested against fixtures, but a successful live
    response with valid parsed records has never been observed. A timeout does
    not prove the key is invalid; it proves nothing about key validity.
11. **No price forecast.** No verified historical price observations exist, so
    no forecast error metric can be computed. The forecaster requires at least
    20 chronological observations and is disabled below that.
12. **Weather is modeled, not observed.** Open-Meteo returns modeled conditions
    and forecasts, not on-farm sensor readings.
13. **Vendor inventory and live prices unknown.** No trusted real-time vendor
    inventory integration exists. Resource listings are farmer-submitted and
    not independently verified.
14. **Single-process cache locking.** Market and weather caches are per-process.
    A multi-worker deployment would need shared locking.

## Feature limitations

15. **No disease image classifier.** No trained model or dataset exists in this
    repository. Disease reporting is manual and contextual. No diagnostic
    probability is produced, and none should be claimed.
16. **No notification delivery mechanism.** Notifications are stored and shown
    in-app only. No email, SMS or push delivery exists, and none is claimed.
17. **Reminders are in-app only** for the same reason.
18. **Profit estimates are withheld** where yield or cost references are
    unverified. Recorded expenses and sales are exact; projections are labelled
    as estimates and never as guarantees.
19. **SQLite on ephemeral storage.** Under serverless deployment the database
    lives on a per-instance temporary filesystem and does not persist.
20. **No multilingual support.**
21. **No independent PDF export pipeline.**

## Testing limitations

22. **Browser automation in this run.** Playwright 1.47.0 was installed into
    `.venv` and `scripts/browser_check.py` was executed successfully with exit
    code 0 (see `docs/research/experimental_results.md` E5). Its first execution
    failed because the script was stale — it referenced a `no_soil_test`
    checkbox that an earlier change had removed. After updating the script the
    run passed. One CDN request for the Bootstrap JS bundle returned
    `net::ERR_ABORTED`; this produced no JavaScript error and no HTTP error, and
    is reported rather than omitted.
23. **No coverage measurement.** `coverage.py` is not installed in the
    environment. Statement and branch coverage were not measured.
24. **CSRF is disabled by default under `TESTING`.** CSRF enforcement is tested
    explicitly by enabling `CSRF_ENABLED` in `tests/test_security.py`, which
    matches the production default where `CSRF_ENABLED` resolves to
    `not testing`.
25. **Market integration tested with fixtures only**, never live records.

## Future work, in priority order

1. Obtain a regional crop dataset with a verifiable licence and a geographic or
   temporal key, then run a proper holdout experiment.
2. Expand the literature review to a documented systematic search.
3. Establish live official market access and record real parsed records.
4. Add `coverage.py` and measure coverage on the critical modules.
5. Integrate a legitimate, evaluated disease dataset and model, or keep manual
   reporting and say so.
6. Conduct a farmer user study. This is the only way to evaluate usability or
   outcome claims, and it has never been done.
7. Move to a persistent database if hosted deployment is intended.

## What must never be claimed about this system

- That it will increase a farmer's yield or income.
- That a model confidence score is the probability of profit.
- That any image has been diagnosed by AI.
- That a reminder was delivered by email, SMS or push.
- That market prices shown are live, unless a successful fetch is recorded in
  the same session.
- That the crop dataset is validated for Pune, Maharashtra or India.
