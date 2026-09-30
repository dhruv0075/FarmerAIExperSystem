# Existing SQLite schema

## users

```sql
CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
```

## farms

```sql
CREATE TABLE farms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                farm_name TEXT NOT NULL,
                location_name TEXT,
                latitude REAL,
                longitude REAL,
                area REAL,
                water_source TEXT,
                soil_type TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, area_unit TEXT NOT NULL DEFAULT 'acre', farm_type TEXT NOT NULL DEFAULT 'Irrigated', terrain TEXT, irrigation_type TEXT NOT NULL DEFAULT 'Drip', water_availability TEXT NOT NULL DEFAULT 'Medium', previous_crop TEXT, previous_harvest_date TEXT, preferred_crop_type TEXT DEFAULT 'No preference', risk_preference TEXT DEFAULT 'Balanced', budget_range TEXT, updated_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
```

## soil_records

```sql
CREATE TABLE soil_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                nitrogen REAL,
                phosphorus REAL,
                potassium REAL,
                ph REAL,
                temperature REAL,
                humidity REAL,
                rainfall REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, moisture REAL, has_soil_test INTEGER NOT NULL DEFAULT 1, organic_carbon REAL, electrical_conductivity REAL, micronutrients TEXT,
                FOREIGN KEY(farm_id) REFERENCES farms(id)
            );
```

## crop_recommendations

```sql
CREATE TABLE crop_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                recommended_crop TEXT NOT NULL,
                confidence REAL,
                explanation TEXT,
                input_data TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, selected_crop TEXT,
                FOREIGN KEY(farm_id) REFERENCES farms(id)
            );
```

## crop_cycles

```sql
CREATE TABLE crop_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                crop_name TEXT NOT NULL,
                sowing_date TEXT NOT NULL,
                expected_harvest_date TEXT,
                current_stage TEXT,
                status TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(farm_id) REFERENCES farms(id)
            );
```

## advisories

```sql
CREATE TABLE advisories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_cycle_id INTEGER,
                advisory_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, farm_id INTEGER REFERENCES farms(id),
                FOREIGN KEY(crop_cycle_id) REFERENCES crop_cycles(id)
            );
```

## weather_records

```sql
CREATE TABLE weather_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                temperature REAL,
                humidity REAL,
                rainfall REAL,
                rain_probability REAL,
                wind_speed REAL,
                forecast_date TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, precipitation REAL, raw_payload TEXT, apparent_temperature REAL, wind_gust REAL, et0 REAL, soil_temperature REAL, soil_moisture REAL,
                FOREIGN KEY(farm_id) REFERENCES farms(id)
            );
```

## farm_activities

```sql
CREATE TABLE farm_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_cycle_id INTEGER,
                farm_id INTEGER NOT NULL,
                advisory_id INTEGER,
                activity_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                reason TEXT,
                crop_stage TEXT,
                recommended_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'MEDIUM',
                status TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'COMPLETED', 'SKIPPED')),
                completed_at TEXT,
                skipped_at TEXT,
                farmer_note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, urgency TEXT NOT NULL DEFAULT 'NORMAL', evidence TEXT, rescheduled_date TEXT,
                FOREIGN KEY(crop_cycle_id) REFERENCES crop_cycles(id),
                FOREIGN KEY(farm_id) REFERENCES farms(id),
                FOREIGN KEY(advisory_id) REFERENCES advisories(id)
            );
```

## crop_stages

```sql
CREATE TABLE crop_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_cycle_id INTEGER NOT NULL,
                stage_name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                expected_end_date TEXT,
                actual_end_date TEXT,
                is_current INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'UPCOMING',
                FOREIGN KEY(crop_cycle_id) REFERENCES crop_cycles(id) ON DELETE CASCADE
            );
```

## market_prices

```sql
CREATE TABLE market_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                commodity TEXT NOT NULL,
                variety TEXT,
                market TEXT NOT NULL,
                district TEXT,
                state TEXT,
                min_price REAL,
                max_price REAL,
                modal_price REAL NOT NULL,
                price_date TEXT NOT NULL,
                source TEXT NOT NULL,
                fetch_timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
```

## market_forecasts

```sql
CREATE TABLE market_forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                commodity TEXT NOT NULL,
                market TEXT,
                forecast_period TEXT,
                current_modal_price REAL,
                forecasted_min REAL,
                forecasted_max REAL,
                forecasted_modal REAL,
                trend TEXT,
                confidence TEXT,
                model_name TEXT,
                mae REAL,
                rmse REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
```

## mandis

```sql
CREATE TABLE mandis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                district TEXT,
                state TEXT,
                latitude REAL,
                longitude REAL,
                contact_phone TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
```

## notifications

```sql
CREATE TABLE notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                farm_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                notification_type TEXT NOT NULL DEFAULT 'SYSTEM',
                is_read INTEGER NOT NULL DEFAULT 0,
                link_url TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE
            );
```

## disease_reports

```sql
CREATE TABLE disease_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                crop_cycle_id INTEGER,
                crop TEXT NOT NULL,
                plant_part TEXT NOT NULL,
                problem_category TEXT,
                symptoms TEXT NOT NULL,
                duration_days INTEGER DEFAULT 1,
                affected_area_pct REAL DEFAULT 10.0,
                severity TEXT DEFAULT 'Moderate',
                image_path TEXT,
                farmer_notes TEXT,
                status TEXT NOT NULL DEFAULT 'REPORTED',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE,
                FOREIGN KEY(crop_cycle_id) REFERENCES crop_cycles(id) ON DELETE SET NULL
            );
```

## disease_predictions

```sql
CREATE TABLE disease_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                likely_condition TEXT NOT NULL,
                confidence REAL,
                alternatives_json TEXT,
                weather_context TEXT,
                risk_level TEXT,
                recommendations_json TEXT,
                is_screening INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(report_id) REFERENCES disease_reports(id) ON DELETE CASCADE
            );
```

## fertilizer_recommendations

```sql
CREATE TABLE fertilizer_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                crop_cycle_id INTEGER,
                nitrogen_status TEXT,
                phosphorus_status TEXT,
                potassium_status TEXT,
                primary_recommendation TEXT,
                alternatives_json TEXT,
                timing_guidance TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE
            );
```

## resources

```sql
CREATE TABLE resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                seller_name TEXT,
                address TEXT,
                district TEXT,
                state TEXT,
                latitude REAL,
                longitude REAL,
                contact_phone TEXT,
                is_seller_listed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
```

## resource_prices

```sql
CREATE TABLE resource_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                brand TEXT,
                nutrient_composition TEXT,
                price REAL,
                unit TEXT,
                stock_status TEXT,
                price_status TEXT NOT NULL DEFAULT 'UNAVAILABLE',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(resource_id) REFERENCES resources(id) ON DELETE CASCADE
            );
```

## farm_expenses

```sql
CREATE TABLE farm_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                crop_cycle_id INTEGER,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                vendor TEXT,
                notes TEXT,
                receipt_path TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE,
                FOREIGN KEY(crop_cycle_id) REFERENCES crop_cycles(id) ON DELETE SET NULL
            );
```

## sales

```sql
CREATE TABLE sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                crop_cycle_id INTEGER,
                commodity TEXT NOT NULL,
                sale_date TEXT NOT NULL,
                quantity_sold REAL NOT NULL,
                unit TEXT NOT NULL DEFAULT 'Quintal',
                price_per_unit REAL NOT NULL,
                total_amount REAL NOT NULL,
                market_name TEXT,
                buyer_name TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE,
                FOREIGN KEY(crop_cycle_id) REFERENCES crop_cycles(id) ON DELETE SET NULL
            );
```

## what_if_runs

```sql
CREATE TABLE what_if_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                farm_id INTEGER NOT NULL,
                scenario_name TEXT NOT NULL,
                input_parameters TEXT NOT NULL,
                simulation_results TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE
            );
```

## risk_snapshots

```sql
CREATE TABLE risk_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                crop_cycle_id INTEGER,
                overall_risk REAL NOT NULL,
                weather_risk REAL,
                water_risk REAL,
                nutrient_risk REAL,
                disease_risk REAL,
                market_risk REAL,
                price_risk REAL,
                harvest_risk REAL,
                activity_risk REAL,
                condition_score REAL NOT NULL,
                breakdown_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE
            );
```

## recommendation_feedback

```sql
CREATE TABLE recommendation_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                recommendation_id INTEGER,
                rating TEXT NOT NULL CHECK (rating IN ('USEFUL', 'NOT_USEFUL', 'NOT_APPLICABLE')),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
```