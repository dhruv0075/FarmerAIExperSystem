# Disease Detection Multilingual Integration Report

## Scope

AgriWise AI has a reusable, file-backed translation layer. English (`en`) is
the default and fallback; Marathi (`mr`) and Hindi (`hi`) are available. The
translation layer began with the standalone **Disease Detection** workflow and
has since been applied to shared navigation and a wider set of farm workflows.
The application as a whole is not yet fully multilingual.

## Architecture

- `services/i18n_service.py` loads UTF-8 JSON resources, validates supported
  language codes, resolves dotted translation keys, falls back to English when a
  key is missing, and returns the key rather than a blank string when it is
  missing from every resource.
- `locales/en.json`, `locales/mr.json`, and `locales/hi.json` keep interface
  text organized by module and disease-name mappings separate from interface
  copy. Resources are read as UTF-8.
- The language selector is in the shared header. `POST /language` accepts only
  `en`, `mr`, or `hi`; the choice is stored in Flask's signed session cookie.
  The redirect target is restricted to a local path. Invalid saved values
  resolve to English, and unsupported submitted codes are rejected.
- The Jinja helpers `t` and `td` expose translation lookup to templates. `td`
  uses reviewed resource mappings keyed by the unchanged model class ID, and
  falls back to the English name. The Disease Detection table shows the
  translated display name, English name, and original class ID.
- Disease translation happens only during rendering. The model, image
  preprocessing, class ordering/IDs, inference, and raw score are independent of
  language.
- The existing system Devanagari fonts are preferred for Marathi and Hindi, with
  browser fallback fonts specified in `static/css/product.css`. No runtime
  translation service or external translation API is required.

## Supported languages and translated screens

| Language | Code | Verified content |
|---|---|---|
| English | `en` | Default interface and fallback resource; disease detection, crop recommendation, farm setup, weather, lifecycle, activities, expenses, problem reports, advisories, notifications, account settings, authentication, homepage, dashboard, market, crop comparison, what-if analysis, risk analysis, farm history, farm report, and About |
| मराठी | `mr` | Shared navigation and translated disease, crop recommendation, farm setup, weather, lifecycle, activities, expenses, problem reports, advisories, notifications, account settings, homepage, dashboard, market, crop comparison, what-if analysis, risk analysis, farm history, farm report, and About labels |
| हिन्दी | `hi` | Shared navigation and translated disease, crop recommendation, farm setup, weather, lifecycle, activities, expenses, problem reports, advisories, notifications, account settings, homepage, dashboard, market, crop comparison, what-if analysis, risk analysis, farm history, farm report, and About labels |

The shared header, language selector, core workflow labels and selected empty
states use the same translation lookup. Disease Detection includes upload
type/size/dimension errors, crop mismatch, unsupported and unavailable-model
states, closest-class result text, raw-score explanation, model limitations,
dataset browsing directions, and conservative safe-next-step wording. The
disease result and safety wording explicitly avoid treating an unverified
prediction as a diagnosis or chemical-treatment recommendation. Farmer-entered
crop names and database/model identifiers remain unchanged.

Rendered translation assertions cover Disease Detection, expenses, lifecycle,
activities, weather, farm setup, settings, notifications, advisories, problem
reporting, market, crop comparison, what-if analysis, risk analysis, farm
history, farm report, and About in all three languages. Crop-recommendation
resource entries are present in all three locales; the model inputs and
prediction path are unchanged by language.

## Fallback and safety behavior

- An unsupported language in a stored session resets to English. An unsupported
  code submitted to `/language` receives HTTP 400.
- Missing keys in Marathi or Hindi fall back to the English resource. A key
  missing from all resources is shown as its key name, never as a blank label.
- Missing disease-name mappings fall back to the model's English disease name.
- The original machine-readable class ID is never translated or modified.
- Disease-name and safety translations are maintained as local reviewed strings.
  They preserve that predictions are unverified and are not treatment guidance.
  Native-speaker and local agronomist review remains recommended before
  production use, particularly for regional disease terminology.

## Tests and verification

`tests/test_i18n.py` verifies resource coverage for all 38 class IDs, missing-key
fallback, locale refresh when files change, language persistence, rejection of
invalid language codes, local-only redirects, invalid-session fallback, UTF-8
disease-result and validation-error rendering, and page rendering for selected
workflows in all three languages.

`tests/test_disease_detection.py` and `tests/test_disease_model.py` continue to
verify that language selection does not couple to inference and that separate
Disease Detection does not create Problem Reports.

All three locale JSON resources were parsed with duplicate-key detection. The
latest focused localization run completed with **14 tests passing**, and the
full project suite completed with **183 tests passing**. Browser layout checks
at desktop (1265 CSS px) and mobile (375 CSS px) widths reported no horizontal
document overflow; the desktop brand, farm location, and actions occupied
separate aligned header columns.

## Known limitations

- This is not complete application-wide localization. Supporting routes still
  contain untranslated interface copy, including daily/seven-day planning,
  ML analytics, expert-system details, research, transparency, fertilizer and
  resource screens, disease-problem result details, and sales/profit planners.
  These routes must be converted and rendered-tested before the whole
  application can be described as multilingual.
- Some content is data-driven rather than a static interface label and may
  still appear in English: weather-analysis summaries and action reasons,
  previously generated advisory/notification text, user-entered values, and
  dynamic crop or stage names.
- Browser-provided geolocation error details may be appended in the browser's
  own language.
- Marathi and Hindi agricultural terminology has not been independently
  approved by local extension specialists.
- Crop names supplied by users remain as entered. Only dataset disease/class
  names have reviewed display mappings.
- The model's 38 classes exclude Rice. A translated interface does not expand
  model coverage or improve model accuracy.
- The full PlantVillage image dataset remains external; this project includes
  model weights and class labels, not the full image collection.
- The recommendation dataset has not been replaced or expanded. An approved,
  traceable source covering all 14 disease-model crops is still needed before
  making a verified all-crop dataset claim.
