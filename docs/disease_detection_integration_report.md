# Multilingual Integration Report

## Scope

AgriWise AI has a reusable file-backed translation layer. English (`en`) is
the default and fallback; Marathi (`mr`) and Hindi (`hi`) are available.
Standalone disease-image screening has been removed. Problem Report remains a
symptom and reference-photo workflow; it does not classify images or confirm a
diagnosis. The application as a whole is not yet fully multilingual.

## Architecture

- `services/i18n_service.py` loads UTF-8 JSON resources, validates supported
  language codes, resolves dotted translation keys, falls back to English when
  a key is missing, and returns the key rather than a blank label if all
  resources lack it.
- `locales/en.json`, `locales/mr.json`, and `locales/hi.json` hold interface
  translations.
- The shared header language selector posts only `en`, `mr`, or `hi` to
  `/language`. The selection is stored in the Flask session and redirects are
  restricted to local paths.
- The Jinja helper `t` provides translated strings. Crop inputs and user-entered
  report values are not transformed by localization.
- System Devanagari fonts are preferred for Marathi and Hindi, with browser
  fallback fonts specified in `static/css/product.css`.

## Supported language coverage

The language resources cover shared navigation and selected content in crop
recommendation, farm setup, weather, lifecycle, activities, expenses, problem
reports, advisories, notifications, account settings, authentication, homepage,
dashboard, market, crop comparison, what-if analysis, risk analysis, farm
history, farm report, and About. Translation completeness across every route,
dynamic value, and hard-coded message is not established.

## Tests and limitations

`tests/test_i18n.py` covers missing-key fallback, locale refresh, language
persistence, invalid-language rejection, local-only redirects, invalid-session
fallback, and selected translated routes. Disease image-screening strings and
model class-label translations are no longer used by the application.

Some weather/action summaries, previously generated advisory text, user-entered
values, and dynamic crop or stage names may remain in English. Marathi and Hindi
agricultural terminology has not been independently approved by local
extension specialists.
