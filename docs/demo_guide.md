# Demo

PowerShell in the project root:

```powershell
python -m pip install -r requirements.txt
python ml/train_model.py
python app.py
```

Optional disease-image screening dependencies: `python -m pip install -r requirements-disease.txt`.

Open http://127.0.0.1:5000. Register a new account, select manual location, enter 18.5 / 73.8 and your own farm name/location. Choose soil-test unavailable if measurements do not exist. Dashboard ? Weather ? Crop Planner. For an explicitly synthetic test account only, use N=90 P=42 K=43 pH=6.5 temperature=20.8 humidity=82 rainfall=210 moisture=24. These are test inputs, not recommended field values.

Select a crop, confirm its actual sowing date, generate advisories, create/complete an irrigation activity, rerun reasoning, and verify pending/skipped tasks are not counted as completed. Record an expense and sale, view actual profit, and keep the workflows separate: use Disease Detection to screen an image transiently, then use Problem Report only to save symptoms/reference photos. Model suggestions are unverified and no disease accuracy score is available. Open the PlantVillage link on Disease Detection to browse the full dataset online; the project bundles its model and 38 labels, not all dataset images. Log out/in and verify persistence. Market data may be unavailable when the government endpoint cannot connect.

```powershell
python -m pytest -q
python -m pip install playwright
python scripts/browser_check.py
```

Browser check uses locally installed Microsoft Edge and a temporary database on port 5056. API key and stable session secret belong in ignored .env; shell environment overrides .env.
