from __future__ import annotations

import sqlite3
import secrets
from pathlib import Path
from typing import Optional
from config import DATABASE_PATH

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = DATABASE_PATH


def get_db_connection(database_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(database_path: Path | str = DB_PATH) -> None:
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        # 1. users
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                auth_token TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # 2. farms
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS farms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                farm_name TEXT NOT NULL,
                location_name TEXT,
                latitude REAL,
                longitude REAL,
                area REAL NOT NULL DEFAULT 1.0,
                area_unit TEXT NOT NULL DEFAULT 'acre',
                farm_type TEXT NOT NULL DEFAULT 'Irrigated',
                terrain TEXT,
                soil_type TEXT NOT NULL DEFAULT 'Black',
                water_source TEXT NOT NULL DEFAULT 'Well',
                irrigation_type TEXT NOT NULL DEFAULT 'Drip',
                water_availability TEXT NOT NULL DEFAULT 'Medium',
                previous_crop TEXT,
                previous_harvest_date TEXT,
                preferred_crop_type TEXT DEFAULT 'No preference',
                risk_preference TEXT DEFAULT 'Balanced',
                budget_range TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # 3. soil_records
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS soil_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                nitrogen REAL NOT NULL DEFAULT 70.0,
                phosphorus REAL NOT NULL DEFAULT 40.0,
                potassium REAL NOT NULL DEFAULT 40.0,
                ph REAL NOT NULL DEFAULT 6.5,
                moisture REAL,
                organic_carbon REAL,
                electrical_conductivity REAL,
                micronutrients TEXT,
                has_soil_test INTEGER NOT NULL DEFAULT 1,
                temperature REAL,
                humidity REAL,
                rainfall REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE
            )
            """
        )

        # 4. crop_recommendations
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS crop_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                recommended_crop TEXT NOT NULL,
                selected_crop TEXT,
                confidence REAL,
                decision_score REAL,
                explanation TEXT,
                agronomic_compatibility REAL,
                weather_compatibility REAL,
                market_attractiveness REAL,
                input_data TEXT,
                top_candidates TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE
            )
            """
        )

        # 5. crop_cycles
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS crop_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                crop_name TEXT NOT NULL,
                sowing_date TEXT NOT NULL,
                expected_harvest_date TEXT,
                current_stage TEXT NOT NULL DEFAULT 'Germination',
                stage_progress REAL NOT NULL DEFAULT 0.0,
                status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (UPPER(status) IN ('ACTIVE', 'COMPLETED', 'ABANDONED', 'HARVESTED')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE
            )
            """
        )

        # 6. crop_stages
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS crop_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_cycle_id INTEGER NOT NULL,
                stage_name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                expected_end_date TEXT,
                actual_end_date TEXT,
                is_current INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'UPCOMING',
                FOREIGN KEY(crop_cycle_id) REFERENCES crop_cycles(id) ON DELETE CASCADE
            )
            """
        )

        # 7. weather_records
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                temperature REAL,
                apparent_temperature REAL,
                humidity REAL,
                precipitation REAL,
                rain_probability REAL,
                wind_speed REAL,
                wind_gust REAL,
                et0 REAL,
                soil_temperature REAL,
                soil_moisture REAL,
                forecast_date TEXT,
                raw_payload TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE
            )
            """
        )

        # 8. market_prices
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market_prices (
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
            )
            """
        )

        # 9. market_forecasts
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market_forecasts (
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
            )
            """
        )

        # 10. mandis
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mandis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                district TEXT,
                state TEXT,
                latitude REAL,
                longitude REAL,
                contact_phone TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # 11. advisories
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS advisories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_cycle_id INTEGER,
                farm_id INTEGER NOT NULL,
                advisory_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'INFO',
                reason TEXT,
                evidence TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(crop_cycle_id) REFERENCES crop_cycles(id) ON DELETE SET NULL,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE
            )
            """
        )

        # 12. notifications
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
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
            )
            """
        )

        # 13. farm_activities
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS farm_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_cycle_id INTEGER,
                farm_id INTEGER NOT NULL,
                advisory_id INTEGER,
                activity_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                reason TEXT,
                evidence TEXT,
                crop_stage TEXT,
                recommended_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'MEDIUM',
                urgency TEXT NOT NULL DEFAULT 'NORMAL',
                status TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK (UPPER(status) IN ('UPCOMING', 'PENDING', 'COMPLETED', 'SKIPPED', 'RESCHEDULED', 'OVERDUE')),
                completed_at TEXT,
                skipped_at TEXT,
                rescheduled_date TEXT,
                farmer_note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(crop_cycle_id) REFERENCES crop_cycles(id) ON DELETE CASCADE,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE,
                FOREIGN KEY(advisory_id) REFERENCES advisories(id) ON DELETE SET NULL
            )
            """
        )

        # 14. disease_reports
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS disease_reports (
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
            )
            """
        )

        # 15. disease_predictions
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS disease_predictions (
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
            )
            """
        )

        # 16. fertilizer_recommendations
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS fertilizer_recommendations (
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
            )
            """
        )

        # 17. resources
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS resources (
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
            )
            """
        )

        # 18. resource_prices
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS resource_prices (
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
            )
            """
        )

        # 19. farm_expenses
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS farm_expenses (
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
            )
            """
        )

        # 20. sales
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sales (
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
            )
            """
        )

        # 21. what_if_runs
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS what_if_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                farm_id INTEGER NOT NULL,
                scenario_name TEXT NOT NULL,
                input_parameters TEXT NOT NULL,
                simulation_results TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE CASCADE
            )
            """
        )

        # 22. risk_snapshots
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS risk_snapshots (
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
            )
            """
        )

        # 23. recommendation_feedback
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recommendation_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                recommendation_id INTEGER,
                rating TEXT NOT NULL CHECK (rating IN ('USEFUL', 'NOT_USEFUL', 'NOT_APPLICABLE')),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # Indexes for query performance and data isolation
        conn.execute("CREATE INDEX IF NOT EXISTS idx_farms_user ON farms(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_farm_status ON farm_activities(farm_id, status, due_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cycles_farm_status ON crop_cycles(farm_id, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, is_read)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expenses_farm_cycle ON farm_expenses(farm_id, crop_cycle_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_farm_cycle ON sales(farm_id, crop_cycle_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_disease_farm ON disease_reports(farm_id)")

        # Handle backward compatibility column migrations if old database exists
        _apply_migrations(conn)

        conn.commit()


def _apply_migrations(conn: sqlite3.Connection) -> None:
    """Safely adds missing columns to existing database tables if they originated from earlier version."""
    user_cols = {row[1] for row in conn.execute('PRAGMA table_info(users)')}
    if 'auth_token' not in user_cols:
        conn.execute('ALTER TABLE users ADD COLUMN auth_token TEXT')
    for row in conn.execute('SELECT id FROM users WHERE auth_token IS NULL OR auth_token = ""').fetchall():
        conn.execute('UPDATE users SET auth_token = ? WHERE id = ?', (secrets.token_urlsafe(32), row[0]))

    weather_cols = {row[1] for row in conn.execute('PRAGMA table_info(weather_records)')}
    for column, sql_type in {'precipitation': 'REAL', 'raw_payload': 'TEXT', 'apparent_temperature': 'REAL', 'wind_gust': 'REAL', 'et0': 'REAL', 'soil_temperature': 'REAL', 'soil_moisture': 'REAL'}.items():
        if column not in weather_cols:
            conn.execute(f'ALTER TABLE weather_records ADD COLUMN {column} {sql_type}')
    if 'rainfall' in weather_cols:
        conn.execute('UPDATE weather_records SET precipitation=rainfall WHERE precipitation IS NULL')
    advisory_cols = {row[1] for row in conn.execute('PRAGMA table_info(advisories)')}
    if 'farm_id' not in advisory_cols:
        conn.execute('ALTER TABLE advisories ADD COLUMN farm_id INTEGER REFERENCES farms(id)')
        conn.execute('UPDATE advisories SET farm_id=(SELECT farm_id FROM crop_cycles WHERE id=advisories.crop_cycle_id)')
    farm_cols = {row[1] for row in conn.execute("PRAGMA table_info(farms)").fetchall()}
    if "area_unit" not in farm_cols:
        conn.execute("ALTER TABLE farms ADD COLUMN area_unit TEXT NOT NULL DEFAULT 'acre'")
    if "farm_type" not in farm_cols:
        conn.execute("ALTER TABLE farms ADD COLUMN farm_type TEXT NOT NULL DEFAULT 'Irrigated'")
    if "terrain" not in farm_cols:
        conn.execute("ALTER TABLE farms ADD COLUMN terrain TEXT")
    if "irrigation_type" not in farm_cols:
        conn.execute("ALTER TABLE farms ADD COLUMN irrigation_type TEXT NOT NULL DEFAULT 'Drip'")
    if "water_availability" not in farm_cols:
        conn.execute("ALTER TABLE farms ADD COLUMN water_availability TEXT NOT NULL DEFAULT 'Medium'")
    if "previous_crop" not in farm_cols:
        conn.execute("ALTER TABLE farms ADD COLUMN previous_crop TEXT")
    if "previous_harvest_date" not in farm_cols:
        conn.execute("ALTER TABLE farms ADD COLUMN previous_harvest_date TEXT")
    if "preferred_crop_type" not in farm_cols:
        conn.execute("ALTER TABLE farms ADD COLUMN preferred_crop_type TEXT DEFAULT 'No preference'")
    if "risk_preference" not in farm_cols:
        conn.execute("ALTER TABLE farms ADD COLUMN risk_preference TEXT DEFAULT 'Balanced'")
    if "budget_range" not in farm_cols:
        conn.execute("ALTER TABLE farms ADD COLUMN budget_range TEXT")
    if "updated_at" not in farm_cols:
        conn.execute("ALTER TABLE farms ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")

    soil_cols = {row[1] for row in conn.execute("PRAGMA table_info(soil_records)").fetchall()}
    if "has_soil_test" not in soil_cols:
        conn.execute("ALTER TABLE soil_records ADD COLUMN has_soil_test INTEGER NOT NULL DEFAULT 1")
    if "organic_carbon" not in soil_cols:
        conn.execute("ALTER TABLE soil_records ADD COLUMN organic_carbon REAL")
    if "electrical_conductivity" not in soil_cols:
        conn.execute("ALTER TABLE soil_records ADD COLUMN electrical_conductivity REAL")
    if "micronutrients" not in soil_cols:
        conn.execute("ALTER TABLE soil_records ADD COLUMN micronutrients TEXT")

    act_cols = {row[1] for row in conn.execute("PRAGMA table_info(farm_activities)").fetchall()}
    if "urgency" not in act_cols:
        conn.execute("ALTER TABLE farm_activities ADD COLUMN urgency TEXT NOT NULL DEFAULT 'NORMAL'")
    if "evidence" not in act_cols:
        conn.execute("ALTER TABLE farm_activities ADD COLUMN evidence TEXT")
    if "rescheduled_date" not in act_cols:
        conn.execute("ALTER TABLE farm_activities ADD COLUMN rescheduled_date TEXT")
