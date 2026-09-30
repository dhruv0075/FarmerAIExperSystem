# Demo

PowerShell in the project root:

```powershell
python -m pip install -r requirements.txt
python ml/train_model.py
python app.py
```

Open http://127.0.0.1:5000. Register a new account, select manual location, enter 18.5 / 73.8 and your own farm name/location. Choose soil-test unavailable if measurements do not exist. Dashboard ? Weather ? Crop Planner. For an explicitly synthetic test account only, use N=90 P=42 K=43 pH=6.5 temperature=20.8 humidity=82 rainfall=210 moisture=24. These are test inputs, not recommended field values.

Select a crop, confirm its actual sowing date, generate advisories, create/complete an irrigation activity, rerun reasoning, and verify pending/skipped tasks are not counted as completed. Record an expense and sale, view actual profit, report symptoms, open the report, log out/in and verify persistence. Market data may be unavailable when the government endpoint cannot connect. No image diagnosis is claimed.

```powershell
python -m pytest -q
python -m pip install playwright
python scripts/browser_check.py
```

Browser check uses locally installed Microsoft Edge and a temporary database on port 5056. API key and stable session secret belong in ignored .env; shell environment overrides .env.
