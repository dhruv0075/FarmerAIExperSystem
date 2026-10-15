# Disease Detection Multilingual Integration Report

## Scope

AgriWise AI now has a reusable, file-backed translation layer, initially applied to
the standalone **Disease Detection** screen. English (`en`) is the default and
fallback; Marathi (`mr`) and Hindi (`hi`) are supported on that screen. Other
application modules have not been translated, so the application as a whole is
not yet multilingual.

## Architecture

- `services/i18n_service.py` loads UTF-8 JSON resources, validates supported
  language codes, resolves dotted translation keys, falls back to English when a
  key is missing, and returns the key rather than a blank string when it is
  missing from every resource.
- `locales/en.json`, `locales/mr.json`, and `locales/hi.json` keep interface text
  and disease-name mappings organized by resource section.
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
| English | `en` | Disease Detection form, dataset information, model result, safety warnings and validation errors |
| मराठी | `mr` | रोग ओळख form, dataset information, translated disease names, model result, warnings and validation errors |
| हिन्दी | `hi` | रोग पहचान form, dataset information, translated disease names, model result, warnings and validation errors |

Translated content includes upload type/size/dimension errors, crop mismatch,
unsupported and unavailable-model states, closest-class result text, raw-score
explanation, limits of the model, dataset browsing directions, and conservative
safe-next-step wording. The text explicitly avoids diagnosing or recommending
chemical treatment from an unverified model result. Farmer-entered crop names
are user data and are not machine-translated.

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
fallback, language persistence, rejection of invalid language codes, local-only
redirects, invalid-session fallback, UTF-8 Marathi/Hindi result rendering, and
localized upload validation.

`tests/test_disease_detection.py` and `tests/test_disease_model.py` continue to
verify that language selection does not couple to inference and that separate
Disease Detection does not create Problem Reports.

The focused multilingual, disease, model, route, report-flow, and black-box
regression run completed with **112 tests passing**.

## Known limitations

- Only Disease Detection is translated; other routes intentionally remain
  English pending their own integration and tests.
- Marathi and Hindi agricultural terminology has not been independently
  approved by local extension specialists.
- Crop names supplied by users remain as entered. Only dataset disease/class
  names have reviewed display mappings.
- The model's 38 classes exclude Rice. A translated interface does not expand
  model coverage or improve model accuracy.
- The full PlantVillage image dataset remains external; this project includes
  model weights and class labels, not the full image collection.
