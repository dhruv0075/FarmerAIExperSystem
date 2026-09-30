from __future__ import annotations

import json
import os
import sqlite3
import uuid
import math
import io
import secrets
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import (
    Flask,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    send_from_directory,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError
from dotenv import load_dotenv
from config import UPLOAD_DIR

from db import DB_PATH, get_db_connection, init_db as db_init
from services.activity_service import (
    generate_stage_activities,
    get_activity_counts,
    is_overdue,
)
from services.crop_decision_service import rank_and_explain_crops
from services.crop_ml_service import (
    get_model_evaluation_metrics,
    predict_crop_ml,
)
from services.crop_service import (
    compare_crop_dataset_fit,
    ensure_model_exists,
    predict_crop,
)
from services.decision_orchestrator import (
    FarmState,
    build_seven_day_action_plan,
    build_unified_daily_farm_plan,
)
from services.disease_service import (
    analyze_crop_issue,
    get_past_problem_reports,
)
from services.expert_system import (
    evaluate_expert_system,
    generate_advisories,
)
from services.explanation_service import build_explanation
from services.fertilizer_service import analyze_nutrients_and_advise
from services.lifecycle_service import (
    get_all_supported_crops,
    get_crop_stage_summary,
    get_lifecycle_profile,
)
from services.location_service import (
    get_default_farm_location,
    is_valid_coordinates,
    reverse_geocode,
)
from services.market_forecast_service import generate_price_forecast
from services.market_service import (
    get_all_commodities,
    get_market_prices_for_commodity,
)
from services.notification_service import (
    create_notification,
    get_user_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)
from services.profit_service import (
    aggregate_farm_financials,
    calculate_crop_profit_potential,
)
from services.report_service import generate_comprehensive_farm_report
from services.resource_service import (
    get_nearby_resources,
    get_resource_types,
)
from services.risk_service import (
    analyze_comprehensive_farm_risk,
    analyze_farm_risk,
)
from services.weather_analysis import analyze_forecast
from services.weather_service import WeatherError, fetch_weather_data

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')
UPLOAD_FOLDER = UPLOAD_DIR
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = get_db_connection(current_app.config["DATABASE"])
        g.db = conn
    return g.db


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def get_current_user() -> Optional[Dict[str, Any]]:
    user_id = session.get("user_id")
    if not user_id:
        return None
    row = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_user_farm(user_id: int) -> Optional[Dict[str, Any]]:
    row = get_db().execute(
        "SELECT * FROM farms WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    return dict(row) if row else None


def get_latest_soil_record(farm_id: int) -> Optional[Dict[str, Any]]:
    row = get_db().execute(
        "SELECT * FROM soil_records WHERE farm_id = ? ORDER BY id DESC LIMIT 1",
        (farm_id,),
    ).fetchone()
    return dict(row) if row else None


def get_latest_cycle(farm_id: int) -> Optional[Dict[str, Any]]:
    row = get_db().execute(
        "SELECT * FROM crop_cycles WHERE farm_id = ? ORDER BY id DESC LIMIT 1",
        (farm_id,),
    ).fetchone()
    if not row:
        return None
    cycle = dict(row)
    cycle.update(get_crop_stage_summary(cycle["crop_name"], cycle["sowing_date"]))
    return cycle


def get_latest_weather(farm_id: int) -> Optional[Dict[str, Any]]:
    row = get_db().execute(
        "SELECT * FROM weather_records WHERE farm_id = ? ORDER BY id DESC LIMIT 1",
        (farm_id,),
    ).fetchone()
    return dict(row) if row else None


def get_latest_recommendation(farm_id: int) -> Optional[Dict[str, Any]]:
    row = get_db().execute(
        "SELECT * FROM crop_recommendations WHERE farm_id = ? ORDER BY id DESC LIMIT 1",
        (farm_id,),
    ).fetchone()
    return dict(row) if row else None


def load_farm_state_object(db: sqlite3.Connection, farm_id: int, user_id: int) -> FarmState:
    farmer = dict(db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone() or {})
    farm = dict(db.execute("SELECT * FROM farms WHERE id = ?", (farm_id,)).fetchone() or {})
    soil_row = db.execute("SELECT * FROM soil_records WHERE farm_id = ? ORDER BY id DESC LIMIT 1", (farm_id,)).fetchone()
    soil = dict(soil_row) if soil_row else {}
    cycle_row = db.execute("SELECT * FROM crop_cycles WHERE farm_id = ? ORDER BY id DESC LIMIT 1", (farm_id,)).fetchone()
    cycle = dict(cycle_row) if cycle_row else None
    if cycle:
        cycle.update(get_crop_stage_summary(cycle["crop_name"], cycle["sowing_date"]))

    weather_row = db.execute("SELECT * FROM weather_records WHERE farm_id = ? ORDER BY id DESC LIMIT 1", (farm_id,)).fetchone()
    weather = {"current": dict(weather_row)} if weather_row else {"current": {}}
    if farm.get("latitude") and farm.get("longitude"):
        try:
            weather = fetch_weather_data(float(farm["latitude"]), float(farm["longitude"]))
        except Exception:
            pass

    act_rows = db.execute("SELECT * FROM farm_activities WHERE farm_id = ? ORDER BY due_date ASC", (farm_id,)).fetchall()
    activities = [dict(r) for r in act_rows]

    dr_rows = db.execute("SELECT * FROM disease_reports WHERE farm_id = ? ORDER BY id DESC", (farm_id,)).fetchall()
    disease_reports = [dict(r) for r in dr_rows]

    exp_rows = db.execute("SELECT * FROM farm_expenses WHERE farm_id = ? ORDER BY date DESC", (farm_id,)).fetchall()
    expenses = [dict(r) for r in exp_rows]

    sales_rows = db.execute("SELECT * FROM sales WHERE farm_id = ? ORDER BY sale_date DESC", (farm_id,)).fetchall()
    sales = [dict(r) for r in sales_rows]

    return FarmState(
        farmer=farmer,
        farm=farm,
        soil=soil,
        crop_cycle=cycle,
        weather=weather,
        activities=activities,
        disease_reports=disease_reports,
        expenses=expenses,
        sales=sales,
    )


def create_app(test_config=None) -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("AGRIWISE_SECRET_KEY") or os.urandom(32)
    app.config["DATABASE"] = str(DB_PATH)
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB max upload
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('AGRIWISE_SECURE_COOKIES', '').lower() == 'true'
    if os.environ.get('AGRIWISE_ENV') == 'production' and not os.environ.get('AGRIWISE_SECRET_KEY'):
        raise RuntimeError('AGRIWISE_SECRET_KEY must be configured in production.')
    if test_config:
        app.config.update(test_config)

    @app.teardown_appcontext
    def close_db(_):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    db_init(app.config["DATABASE"])
    # Missing models are handled at prediction time; startup must not retrain.

    @app.before_request
    def load_global_context():
        session.setdefault('csrf_token', secrets.token_urlsafe(32))
        if request.method == 'POST' and current_app.config.get('CSRF_ENABLED', not current_app.testing):
            supplied = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token', '')
            if not secrets.compare_digest(supplied, session['csrf_token']):
                return render_template('error.html', message='Form expired. Reload the page and try again.'), 400
        if request.path.startswith('/static/uploads/'):
            return render_template('error.html', message='Use the authorized report image link.'), 403
        g.current_user = get_current_user()
        if g.current_user:
            g.current_farm = get_user_farm(g.current_user["id"])
            try:
                row = get_db().execute(
                    "SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND is_read = 0",
                    (g.current_user["id"],),
                ).fetchone()
                g.unread_notifications = row["c"] if row else 0
            except Exception:
                g.unread_notifications = 0
        else:
            g.current_farm = None
            g.unread_notifications = 0

    @app.context_processor
    def inject_template_globals():
        return {
            "current_user": g.get("current_user"),
            "user": g.get("current_user"),
            "current_farm": g.get("current_farm"),
            "farm": g.get("current_farm"),
            "unread_notifications_count": g.get("unread_notifications", 0),
            "csrf_token": session.get('csrf_token', ''),
        }

    # ==========================================
    # AUTHENTICATION & ONBOARDING
    # ==========================================

    @app.route('/healthz')
    def health_check():
        get_db().execute('SELECT 1').fetchone()
        return jsonify(status='ok')

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = (request.form.get("name") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""

            if not name or not email or len(password) < 6:
                flash("Please provide a valid name, email, and password (min 6 characters).", "danger")
                return render_template("register.html")

            if get_db().execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
                flash("This email address is already registered.", "warning")
                return render_template("register.html")

            hashed = generate_password_hash(password)
            cursor = get_db().execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, hashed),
            )
            get_db().commit()
            session["user_id"] = cursor.lastrowid
            flash("Welcome to AgriWise AI! Please configure your farm location to begin.", "success")
            return redirect(url_for("farm_setup"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""
            row = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if row and check_password_hash(row["password_hash"], password):
                session["user_id"] = row["id"]
                farm = get_user_farm(row["id"])
                flash("Welcome back to AgriWise AI.", "success")
                if not farm:
                    return redirect(url_for("farm_setup"))
                return redirect(url_for("dashboard"))
            flash("Invalid email or password.", "danger")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been logged out securely.", "info")
        return redirect(url_for("login"))

    # ==========================================
    # FARM SETUP WIZARD & PROFILE
    # ==========================================

    @app.route("/farm/setup", methods=["GET", "POST"])
    @login_required
    def farm_setup():
        user = get_current_user()
        farm = get_user_farm(user["id"])

        if request.method == "POST":
            farm_name = (request.form.get("farm_name") or "").strip()
            location_name = (request.form.get("location_name") or "").strip()
            latitude = request.form.get("latitude")
            longitude = request.form.get("longitude")
            area = request.form.get("area") or "1.0"
            area_unit = request.form.get("area_unit") or "acre"
            water_source = (request.form.get("water_source") or "Well").strip()
            soil_type = (request.form.get("soil_type") or "Black").strip()
            irrigation_type = (request.form.get("irrigation_type") or "Drip").strip()
            water_availability = (request.form.get("water_availability") or "Medium").strip()
            previous_crop = (request.form.get("previous_crop") or "").strip()

            if not farm_name:
                flash("Farm name is required.", "danger")
                return render_template("farm_setup.html", farm=farm)

            try:
                area_val = float(area)
                if not math.isfinite(area_val) or area_val <= 0:
                    raise ValueError
            except ValueError:
                flash("Farm area must be a positive number.", "danger")
                return render_template("farm_setup.html", farm=farm)

            lat_val = None
            lon_val = None
            if latitude and longitude:
                try:
                    lat_val = float(latitude)
                    lon_val = float(longitude)
                    if not is_valid_coordinates(lat_val, lon_val):
                        raise ValueError
                except ValueError:
                    flash("Coordinates are invalid. Latitude must be -90..90 and Longitude -180..180.", "danger")
                    return render_template("farm_setup.html", farm=farm)

            if farm:
                get_db().execute(
                    """
                    UPDATE farms
                    SET farm_name = ?, location_name = ?, latitude = ?, longitude = ?, area = ?,
                        area_unit = ?, water_source = ?, soil_type = ?, irrigation_type = ?,
                        water_availability = ?, previous_crop = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (farm_name, location_name, lat_val, lon_val, area_val, area_unit, water_source, soil_type, irrigation_type, water_availability, previous_crop, farm["id"]),
                )
                farm_id = farm["id"]
                flash("Farm profile updated successfully.", "success")
            else:
                cursor = get_db().execute(
                    """
                    INSERT INTO farms
                    (user_id, farm_name, location_name, latitude, longitude, area, area_unit,
                     water_source, soil_type, irrigation_type, water_availability, previous_crop)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user["id"], farm_name, location_name, lat_val, lon_val, area_val, area_unit, water_source, soil_type, irrigation_type, water_availability, previous_crop),
                )
                farm_id = cursor.lastrowid
                flash("Farm initialized! Now explore recommendations and daily planning.", "success")

            get_db().execute("UPDATE farms SET farm_type=?, risk_preference=?, preferred_crop_type=?, previous_harvest_date=?, budget_range=? WHERE id=?",
                (request.form.get('farm_type', 'Mixed'), request.form.get('risk_preference', 'Balanced'), request.form.get('preferred_crop_type', 'No preference'), request.form.get('previous_harvest_date') or None, request.form.get('budget_range'), farm_id))

            # Record baseline soil snapshot if provided
            n_val = request.form.get("nitrogen")
            p_val = request.form.get("phosphorus")
            k_val = request.form.get("potassium")
            ph_val = request.form.get("ph")
            moist_val = request.form.get("moisture")
            if not request.form.get("no_soil_test") and n_val and p_val and k_val and ph_val:
                try:
                    get_db().execute(
                        """
                        INSERT INTO soil_records (farm_id, nitrogen, phosphorus, potassium, ph, moisture, temperature, humidity, rainfall)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (farm_id, float(n_val), float(p_val), float(k_val), float(ph_val), float(moist_val) if moist_val else None, None, None, None),
                    )
                except Exception:
                    pass

            get_db().commit()
            return redirect(url_for("dashboard"))

        default_loc = get_default_farm_location()
        return render_template(
            "farm_setup.html",
            farm=farm,
            default_lat=farm["latitude"] if farm and farm["latitude"] else None,
            default_lon=farm["longitude"] if farm and farm["longitude"] else None,
            default_location=farm["location_name"] if farm and farm["location_name"] else "",
        )

    @app.route("/farm", methods=["GET", "POST"])
    @login_required
    def farm_profile():
        return farm_setup()

    # ==========================================
    # DASHBOARD & ORCHESTRATED PLANNING
    # ==========================================

    @app.route("/dashboard")
    @login_required
    def dashboard():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        if not farm:
            return redirect(url_for("farm_setup"))

        soil = get_latest_soil_record(farm["id"])
        latest_cycle = get_latest_cycle(farm["id"])
        weather = get_latest_weather(farm["id"])
        recommendation = get_latest_recommendation(farm["id"])

        advisories = [dict(r) for r in get_db().execute(
            "SELECT * FROM advisories WHERE crop_cycle_id IN (SELECT id FROM crop_cycles WHERE farm_id = ?) ORDER BY id DESC LIMIT 5",
            (farm["id"],),
        ).fetchall()]

        today = date.today()
        activity_counts = {"pending": 0, "overdue": 0, "due_today": 0, "completed_week": 0}
        activities = [dict(row) for row in get_db().execute(
            "SELECT * FROM farm_activities WHERE farm_id = ? ORDER BY due_date, id DESC LIMIT 8",
            (farm["id"],),
        ).fetchall()]
        for item in activities:
            item["display_status"] = "OVERDUE" if is_overdue(item, today) else item["status"]

        week_start = (today - timedelta(days=6)).isoformat()
        count_row = get_db().execute(
            """SELECT
                 SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) AS pending,
                 SUM(CASE WHEN status = 'PENDING' AND due_date < ? THEN 1 ELSE 0 END) AS overdue,
                 SUM(CASE WHEN status = 'PENDING' AND due_date = ? THEN 1 ELSE 0 END) AS due_today,
                 SUM(CASE WHEN status = 'COMPLETED' AND substr(completed_at, 1, 10) >= ? THEN 1 ELSE 0 END) AS completed_week
               FROM farm_activities WHERE farm_id = ?""",
            (today.isoformat(), today.isoformat(), week_start, farm["id"]),
        ).fetchone()
        if count_row:
            activity_counts = {key: int(count_row[key] or 0) for key in activity_counts}

        farm_analysis = analyze_farm_risk(soil, weather, latest_cycle)
        crop_stage = latest_cycle["current_stage"] if latest_cycle else "Not started"
        progress = 0
        if latest_cycle:
            stage_summary = get_crop_stage_summary(latest_cycle["crop_name"], latest_cycle["sowing_date"])
            progress = stage_summary.get("progress", 0)

        return render_template(
            "dashboard.html",
            user=user,
            farm=farm,
            soil=soil,
            latest_cycle=latest_cycle,
            weather=weather,
            recommendation=recommendation,
            advisories=advisories,
            crop_stage=crop_stage,
            progress=progress,
            activities=activities,
            activity_counts=activity_counts,
            condition_score=farm_analysis["condition_score"],
            condition_components=farm_analysis["condition_components"],
            risk_level=farm_analysis["risk_level"],
            risk_scores=farm_analysis["risk_scores"],
            overall_risk_score=farm_analysis["overall_risk_score"],
        )

    @app.route("/daily-plan")
    @login_required
    def daily_plan_page():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        if not farm:
            flash("Configure your farm profile to view Today's Plan.", "warning")
            return redirect(url_for("farm_setup"))

        farm_state = load_farm_state_object(get_db(), farm["id"], user["id"])
        plan = build_unified_daily_farm_plan(farm_state)
        return render_template("daily_plan.html", plan=plan, farm=farm)

    @app.route("/seven-day-plan")
    @login_required
    def seven_day_plan_page():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        if not farm:
            flash("Configure your farm profile to view the 7-day schedule.", "warning")
            return redirect(url_for("farm_setup"))

        farm_state = load_farm_state_object(get_db(), farm["id"], user["id"])
        plan_days = build_seven_day_action_plan(farm_state)
        return render_template("seven_day_plan.html", plan=plan_days, plan_days=plan_days, farm=farm, today=date.today().isoformat())

    # ==========================================
    # TWO-LEVEL CROP RECOMMENDATION & LIFECYCLE
    # ==========================================

    @app.route("/crop-recommendation", methods=["GET", "POST"])
    @login_required
    def crop_recommendation():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        if not farm:
            flash("Please set up your farm profile before running crop planning.", "warning")
            return redirect(url_for("farm_setup"))

        soil = get_latest_soil_record(farm["id"])

        if request.method == "POST":
            try:
                moisture_val = (request.form.get("moisture") or "").strip()
                stage_data = {
                    "nitrogen": float(request.form.get("nitrogen", "")),
                    "phosphorus": float(request.form.get("phosphorus", "")),
                    "potassium": float(request.form.get("potassium", "")),
                    "ph": float(request.form.get("ph", "")),
                    "temperature": float(request.form.get("temperature", "")),
                    "humidity": float(request.form.get("humidity", "")),
                    "rainfall": float(request.form.get("rainfall", "")),
                    "moisture": float(moisture_val) if moisture_val else None,
                }
            except ValueError:
                flash("Enter valid numeric values for all soil and climate inputs.", "danger")
                return render_template("crop_recommendation.html", farm=farm, soil=soil)

            if (not all(math.isfinite(v) for v in stage_data.values() if v is not None)
                or not 0 <= stage_data["ph"] <= 14
                or not 0 <= stage_data["humidity"] <= 100
                or any(stage_data[k] < 0 for k in ('nitrogen', 'phosphorus', 'potassium', 'rainfall'))
                or (stage_data['moisture'] is not None and not 0 <= stage_data['moisture'] <= 100)):
                flash("Enter finite values: pH 0–14, humidity/moisture 0–100, and nonnegative nutrients/rainfall.", "danger")
                return render_template("crop_recommendation.html", farm=farm, soil=soil)

            # Persist soil record
            get_db().execute(
                """
                INSERT INTO soil_records (farm_id, nitrogen, phosphorus, potassium, ph, moisture, temperature, humidity, rainfall)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (farm["id"], stage_data["nitrogen"], stage_data["phosphorus"], stage_data["potassium"], stage_data["ph"], stage_data["moisture"], stage_data["temperature"], stage_data["humidity"], stage_data["rainfall"]),
            )

            # Run Level 1 & Level 2 Recommendation
            weather_dict = {"current": {"temperature": stage_data["temperature"], "humidity": stage_data["humidity"], "precipitation": 0.0}}
            farmer_prefs = {
                "risk_preference": request.form.get("risk_preference", "Balanced"),
                "preferred_crop_type": request.form.get("preferred_crop_type", "No preference"),
            }
            ranked_output = rank_and_explain_crops(stage_data, weather_dict, farm, farmer_prefs)
            top_winner = ranked_output["decision_ranked_crops"][0] if ranked_output["decision_ranked_crops"] else None

            # ML Level 1 raw output
            ml_pred = predict_crop(stage_data)
            explanation = build_explanation(ml_pred, stage_data)

            # Insert into crop_recommendations
            rec_cursor = get_db().execute(
                """
                INSERT INTO crop_recommendations (farm_id, recommended_crop, confidence, explanation, input_data)
                VALUES (?, ?, ?, ?, ?)
                """,
                (farm["id"], top_winner["crop_name"] if top_winner else ml_pred["recommended_crop"], top_winner["ml_probability"] if top_winner else ml_pred["confidence"], json.dumps(explanation), json.dumps(stage_data)),
            )
            get_db().commit()

            return render_template(
                "recommendation_result.html",
                result=ml_pred,
                explanation=explanation,
                farm=farm,
                soil=stage_data,
                ranked_output=ranked_output,
                recommendation_id=rec_cursor.lastrowid,
            )

        return render_template("crop_recommendation.html", farm=farm, soil=soil)

    @app.route("/recommendations/<int:recommendation_id>/select", methods=["POST"])
    @login_required
    def select_recommendation_crop(recommendation_id):
        farm = get_user_farm(get_current_user()["id"])
        selected_crop = (request.form.get("selected_crop") or "").strip()
        if not farm:
            flash("Create a farm profile before selecting a crop.", "warning")
            return redirect(url_for("farm_setup"))

        supported_crops = get_all_supported_crops()
        from services.suitability_service import get_crop_knowledge
        aliases = {key.lower(): key for key in supported_crops}
        aliases.update({info.get("name", key).lower(): key for key, info in get_crop_knowledge().items()})
        crop_key = aliases.get(selected_crop.lower())
        if crop_key is None:
            flash(f"Crop '{selected_crop}' is not in the supported crop taxonomy.", "danger")
            return redirect(url_for("crop_recommendation"))

        owned = get_db().execute("SELECT id FROM crop_recommendations WHERE id = ? AND farm_id = ?", (recommendation_id, farm["id"])).fetchone()
        if not owned:
            return render_template("error.html", message="Recommendation not found."), 404
        get_db().execute(
            "UPDATE crop_recommendations SET selected_crop = ? WHERE id = ? AND farm_id = ?",
            (selected_crop, recommendation_id, farm["id"]),
        )

        get_db().commit()

        flash(f"{selected_crop} selected. Confirm the actual sowing date to start its lifecycle.", "success")
        return redirect(url_for("lifecycle_page", crop=selected_crop))

    @app.route("/lifecycle", methods=["GET", "POST"])
    @login_required
    def lifecycle_page():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        if not farm:
            flash("Create a farm profile before viewing the crop lifecycle.", "warning")
            return redirect(url_for("farm_setup"))

        cycle = get_latest_cycle(farm["id"])

        if request.method == "POST":
            crop_name = (request.form.get("crop_name") or "").strip().lower()
            sowing_date = (request.form.get("sowing_date") or date.today().isoformat()).strip()
            try:
                date.fromisoformat(sowing_date)
            except ValueError:
                flash("Enter a valid sowing date (YYYY-MM-DD).", "danger")
                return redirect(url_for("lifecycle_page"))

            summary = get_crop_stage_summary(crop_name, sowing_date)
            get_db().execute(
                """
                INSERT INTO crop_cycles (farm_id, crop_name, sowing_date, expected_harvest_date, current_stage, status)
                VALUES (?, ?, ?, ?, ?, 'active')
                """,
                (farm["id"], crop_name, sowing_date, summary["expected_harvest_date"], summary["current_stage"]),
            )
            get_db().commit()
            flash(f"Crop lifecycle for {crop_name.title()} started successfully.", "success")
            return redirect(url_for("lifecycle_page"))

        selected_crop = request.args.get("crop", cycle["crop_name"] if cycle else "wheat")
        lifecycle_profile = get_lifecycle_profile(selected_crop)

        return render_template(
            "crop_lifecycle.html",
            cycle=cycle,
            farm=farm,
            lifecycle_profile=lifecycle_profile,
            all_crops=get_all_supported_crops(),
            today=date.today().isoformat(),
            selected_crop=selected_crop,
        )

    # ==========================================
    # EXPERT SYSTEM & ADVISORIES
    # ==========================================

    @app.route("/expert-system")
    @login_required
    def expert_system_page():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        cycle = get_latest_cycle(farm["id"]) if farm else None
        soil = get_latest_soil_record(farm["id"]) if farm else None
        weather_row = get_latest_weather(farm["id"]) if farm else None

        history = [dict(row) for row in get_db().execute(
            "SELECT activity_type, status, completed_at, title FROM farm_activities WHERE farm_id = ? AND status = 'COMPLETED' ORDER BY completed_at DESC LIMIT 30",
            (farm["id"] if farm else 0,),
        ).fetchall()] if farm else []

        stage = cycle.get("current_stage", "Vegetative") if cycle else "Vegetative"
        crop = cycle.get("crop_name", "General Crop") if cycle else "General Crop"
        current_weather = {"current": dict(weather_row)} if weather_row else {"current": {}}

        expert_data = evaluate_expert_system(crop, stage, current_weather, soil or {}, [], history)

        return render_template(
            "expert_system.html",
            farm=farm,
            cycle=cycle,
            soil=soil,
            weather=weather_row,
            activity_history=history,
            expert_data=expert_data,
            rules=expert_data["advisories"],
        )

    @app.route("/advisories")
    @login_required
    def advisories():
        farm = get_user_farm(get_current_user()["id"])
        rows = []
        if farm:
            rows = get_db().execute(
                "SELECT a.* FROM advisories a JOIN crop_cycles c ON c.id = a.crop_cycle_id WHERE c.farm_id = ? ORDER BY a.id DESC",
                (farm["id"],),
            ).fetchall()
        return render_template("advisories.html", advisories=rows, farm=farm)

    @app.route("/advisories/generate", methods=["POST"])
    @login_required
    def generate_farm_advisories():
        farm = get_user_farm(get_current_user()["id"])
        cycle = get_latest_cycle(farm["id"]) if farm else None
        soil = get_latest_soil_record(farm["id"]) if farm else None

        if not farm or not cycle:
            flash("Set up your farm profile and select an active crop before generating advisories.", "warning")
            return redirect(url_for("dashboard"))

        weather_data = {"current": {}}
        if farm.get("latitude") and farm.get("longitude"):
            try:
                weather_data = fetch_weather_data(float(farm["latitude"]), float(farm["longitude"]))
            except Exception:
                pass

        history = [dict(row) for row in get_db().execute(
            "SELECT activity_type, status, completed_at, title FROM farm_activities WHERE farm_id = ? AND status = 'COMPLETED' ORDER BY completed_at DESC LIMIT 30",
            (farm["id"],),
        ).fetchall()]

        stage = cycle.get("current_stage", "Vegetative")
        eval_result = evaluate_expert_system(cycle["crop_name"], stage, weather_data, soil or {}, weather_data.get("forecast", []), history)
        today = date.today().isoformat()

        for adv in eval_result["advisories"]:
            c = get_db().execute(
                """
                INSERT INTO advisories (farm_id, crop_cycle_id, advisory_type, title, message, severity, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (farm["id"], cycle["id"], adv.get("type", "General"), adv.get("title", ""), adv.get("recommendation", adv.get("message", "")), adv.get("severity", "INFO"), adv.get("reason", "")),
            )
            # Create pending task if actionable
            if adv.get("severity") in ["WARNING", "URGENT", "CAUTION"]:
                if get_db().execute("SELECT id FROM farm_activities WHERE farm_id=? AND crop_cycle_id=? AND title=? AND due_date=? AND status='PENDING'", (farm['id'], cycle['id'], adv.get('title', ''), today)).fetchone():
                    continue
                prio = "HIGH" if adv.get("severity") in ["WARNING", "URGENT"] else "MEDIUM"
                get_db().execute(
                    """
                    INSERT INTO farm_activities
                    (crop_cycle_id, farm_id, advisory_id, activity_type, title, description, reason, crop_stage, recommended_date, due_date, priority, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
                    """,
                    (cycle["id"], farm["id"], c.lastrowid, adv.get("type", "General"), adv.get("title", ""), adv.get("recommendation", ""), adv.get("reason", ""), stage, today, today, prio),
                )

        get_db().commit()
        flash(f"Generated {len(eval_result['advisories'])} explainable advisories using weather and confirmed activity history.", "success")
        return redirect(url_for("advisories"))


    # ==========================================
    # FARM ACTIVITIES & CLOSED-LOOP TRACKING
    # ==========================================

    @app.route("/activities")
    @login_required
    def activities_page():
        farm = get_user_farm(get_current_user()["id"])
        activities = []
        if farm:
            query = "SELECT a.*, c.crop_name FROM farm_activities a LEFT JOIN crop_cycles c ON c.id = a.crop_cycle_id WHERE a.farm_id = ?"
            params = [farm["id"]]
            status_filter = (request.args.get("status") or "").upper()
            if status_filter == "OVERDUE":
                query += " AND a.status = 'PENDING' AND a.due_date < ?"
                params.append(date.today().isoformat())
            elif status_filter in ["PENDING", "COMPLETED", "SKIPPED"]:
                query += " AND a.status = ?"
                params.append(status_filter)
            for field, column, operator in [('type', 'a.activity_type', '='), ('crop', 'c.crop_name', '='), ('from', 'a.recommended_date', '>='), ('to', 'a.recommended_date', '<=')]:
                if request.args.get(field):
                    query += f" AND {column} {operator} ?"
                    params.append(request.args[field])

            query += " ORDER BY CASE a.status WHEN 'PENDING' THEN 0 ELSE 1 END, a.due_date, a.id DESC"
            activities = [dict(row) for row in get_db().execute(query, params).fetchall()]
            for item in activities:
                item["display_status"] = "OVERDUE" if is_overdue(item) else item["status"]

        return render_template("activities.html", activities=activities, farm=farm, filters=request.args, today=date.today().isoformat())

    @app.route("/activities/create", methods=["POST"])
    @login_required
    def create_activity():
        farm = get_user_farm(get_current_user()["id"])
        title = (request.form.get("title") or "").strip()
        activity_type = (request.form.get("activity_type") or "Field inspection").strip()
        due_date = (request.form.get("due_date") or date.today().isoformat()).strip()
        description = (request.form.get("description") or "").strip()
        priority = (request.form.get("priority") or "MEDIUM").strip().upper()
        cycle = get_latest_cycle(farm["id"]) if farm else None

        if not farm or not title:
            flash("Activity title is required.", "danger")
            return redirect(url_for("activities_page"))

        get_db().execute(
            """
            INSERT INTO farm_activities
            (crop_cycle_id, farm_id, activity_type, title, description, reason, crop_stage, recommended_date, due_date, priority, status)
            VALUES (?, ?, ?, ?, ?, 'Farmer manual task', ?, ?, ?, ?, 'PENDING')
            """,
            (cycle["id"] if cycle else None, farm["id"], activity_type, title, description, cycle.get("current_stage") if cycle else None, date.today().isoformat(), due_date, priority),
        )
        get_db().commit()
        flash("Activity created as PENDING. Confirmation will update future AI recommendations.", "success")
        return redirect(url_for("activities_page"))

    @app.route("/activities/<int:activity_id>/status", methods=["POST"])
    @login_required
    def update_activity_status(activity_id):
        farm = get_user_farm(get_current_user()["id"])
        activity = get_db().execute(
            "SELECT id, activity_type, crop_cycle_id FROM farm_activities WHERE id = ? AND farm_id = ?",
            (activity_id, farm["id"] if farm else 0),
        ).fetchone()
        if not activity:
            flash("Activity not found for this farm.", "danger")
            return redirect(url_for("activities_page"))

        status = (request.form.get("status") or "").upper()
        note = (request.form.get("farmer_note") or request.form.get("skip_reason") or "").strip()[:1000]
        if status == 'RESCHEDULED':
            try:
                due = date.fromisoformat(request.form.get('rescheduled_date', ''))
            except ValueError:
                return render_template('error.html', message='Enter a valid reschedule date.'), 400
            get_db().execute("UPDATE farm_activities SET status='PENDING', due_date=?, rescheduled_date=?, farmer_note=?, completed_at=NULL, skipped_at=NULL WHERE id=? AND farm_id=?", (due.isoformat(), due.isoformat(), note, activity_id, farm['id']))
            get_db().commit()
            flash('Activity rescheduled; it remains unconfirmed.', 'success')
            return redirect(url_for('activities_page'))

        if status not in {"PENDING", "COMPLETED", "SKIPPED"}:
            flash("Choose a valid activity status.", "danger")
            return redirect(url_for("activities_page"))

        now_str = datetime.now(timezone.utc).isoformat(timespec="seconds")
        completed_at = now_str if status == "COMPLETED" else None
        skipped_at = now_str if status == "SKIPPED" else None

        get_db().execute(
            """
            UPDATE farm_activities
            SET status = ?, completed_at = ?, skipped_at = ?, farmer_note = ?, updated_at = ?
            WHERE id = ? AND farm_id = ?
            """,
            (status, completed_at, skipped_at, note, now_str, activity_id, farm["id"]),
        )
        if status == "COMPLETED" and str(activity["activity_type"]).casefold() == "harvest" and activity["crop_cycle_id"]:
            get_db().execute("UPDATE crop_cycles SET status = 'harvested' WHERE id = ? AND farm_id = ?", (activity["crop_cycle_id"], farm["id"]))

        get_db().commit()
        flash("Activity status recorded. Future advisories use completed actions only.", "success")
        return redirect(url_for("activities_page"))


    # ==========================================
    # CROP PROBLEM / DISEASE REPORTING & DIAGNOSIS
    # ==========================================

    @app.route("/report-problem", methods=["GET", "POST"])
    @login_required
    def report_problem_page():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        cycle = get_latest_cycle(farm["id"]) if farm else None
        default_crop = cycle.get("crop_name", "Wheat") if cycle else "Wheat"
        if not farm:
            return redirect(url_for("farm_setup"))

        if request.method == "POST":
            crop = (request.form.get("crop") or default_crop).strip()
            plant_part = (request.form.get("plant_part") or "Leaf").strip()
            category = (request.form.get("problem_category") or "Unknown").strip()
            symptoms = (request.form.get("symptoms") or "").strip()
            severity = (request.form.get("severity") or "Moderate").strip()
            notes = (request.form.get("farmer_notes") or "").strip()

            saved_filename = None
            image_bytes = None
            if "photo" in request.files:
                file = request.files["photo"]
                if file and file.filename:
                    try:
                        if not allowed_file(file.filename) or file.mimetype not in {'image/jpeg', 'image/png', 'image/webp'}:
                            raise ValueError
                        image_bytes = file.read()
                        with Image.open(io.BytesIO(image_bytes)) as uploaded:
                            if uploaded.format not in {'JPEG', 'PNG', 'WEBP'}:
                                raise ValueError
                            uploaded.verify()
                        file.seek(0)
                    except (ValueError, OSError, UnidentifiedImageError):
                        return render_template("error.html", message="Upload a valid JPEG, PNG, or WebP image."), 400
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_name = f"{uuid.uuid4().hex[:12]}_{filename}"
                    save_path = UPLOAD_FOLDER / unique_name
                    file.seek(0)
                    image_bytes = file.read()
                    with open(save_path, "wb") as f_out:
                        f_out.write(image_bytes)
                    saved_filename = unique_name

            weather_data = {"current": {}}
            if farm and farm.get("latitude") and farm.get("longitude"):
                try:
                    weather_data = fetch_weather_data(float(farm["latitude"]), float(farm["longitude"]))
                except Exception:
                    pass

            diagnosis = analyze_crop_issue(
                crop_name=crop,
                plant_part=plant_part,
                symptoms_text=symptoms,
                category=category,
                weather_data=weather_data,
                image_bytes=image_bytes,
            )

            # Insert report
            rep_cursor = get_db().execute(
                """
                INSERT INTO disease_reports
                (farm_id, crop_cycle_id, crop, plant_part, problem_category, symptoms, severity, image_path, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'screened')
                """,
                (farm["id"] if farm else 0, cycle["id"] if cycle else None, crop, plant_part, category, symptoms, severity, saved_filename),
            )
            report_id = rep_cursor.lastrowid

            # Insert prediction
            primary = diagnosis.get("primary_diagnosis", {})
            get_db().execute(
                """
                INSERT INTO disease_predictions
                (report_id, likely_condition, confidence, risk_level, weather_context, recommendations_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (report_id, primary.get("condition", "Undetermined"), primary.get("confidence"), primary.get("risk_level", "MODERATE"), json.dumps(diagnosis.get("image_analysis", {})), json.dumps(diagnosis)),
            )
            get_db().commit()

            flash("AI diagnostic screening completed successfully.", "success")
            return redirect(url_for("disease_result_page", report_id=report_id))

        past_reports = get_past_problem_reports(farm["id"] if farm else 0, get_db())
        return render_template("report_problem.html", farm=farm, default_crop=default_crop, past_reports=past_reports)

    @app.route("/disease-image/<int:report_id>")
    @login_required
    def disease_image(report_id):
        row = get_db().execute("SELECT d.image_path FROM disease_reports d JOIN farms f ON f.id=d.farm_id WHERE d.id=? AND f.user_id=?", (report_id, session['user_id'])).fetchone()
        if not row or not row['image_path']:
            return render_template('error.html', message='Image not found.'), 404
        folder = UPLOAD_FOLDER if (UPLOAD_FOLDER / row['image_path']).exists() else BASE_DIR / 'static' / 'uploads'
        return send_from_directory(folder, row['image_path'])

    @app.route("/disease-result/<int:report_id>")
    @login_required
    def disease_result_page(report_id):
        farm = get_user_farm(get_current_user()["id"])
        rep_row = get_db().execute(
            "SELECT * FROM disease_reports WHERE id = ? AND farm_id = ?",
            (report_id, farm["id"] if farm else 0),
        ).fetchone()

        if not rep_row:
            flash("Diagnostic report not found.", "danger")
            return redirect(url_for("report_problem_page"))

        pred_row = get_db().execute(
            "SELECT * FROM disease_predictions WHERE report_id = ?",
            (report_id,),
        ).fetchone()

        diagnosis = json.loads(pred_row["recommendations_json"]) if pred_row and pred_row["recommendations_json"] else {}
        return render_template("disease_result.html", report=dict(rep_row), diagnosis=diagnosis, farm=farm)

    # ==========================================
    # FERTILIZER & NUTRIENT ADVISORY
    # ==========================================

    @app.route("/fertilizer", methods=["GET", "POST"])
    @login_required
    def fertilizer_page():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        cycle = get_latest_cycle(farm["id"]) if farm else None
        soil = get_latest_soil_record(farm["id"]) if farm else None
        weather = get_latest_weather(farm["id"]) if farm else None

        crop_name = cycle.get("crop_name", "Wheat") if cycle else "Wheat"
        crop_stage = cycle.get("current_stage", "Vegetative") if cycle else "Vegetative"

        history = [dict(row) for row in get_db().execute(
            "SELECT activity_type, status, completed_at, title FROM farm_activities WHERE farm_id = ? AND status = 'COMPLETED' ORDER BY completed_at DESC LIMIT 30",
            (farm["id"] if farm else 0,),
        ).fetchall()] if farm else []

        weather_dict = {"current": dict(weather)} if weather else {"current": {}}
        plan = analyze_nutrients_and_advise(crop_name, crop_stage, soil or {}, weather_dict, history)

        return render_template("fertilizer.html", farm=farm, cycle=cycle, soil=soil, plan=plan, nut_info=plan)

    # ==========================================
    # AGRICULTURAL RESOURCES & DEALERS
    # ==========================================

    @app.route("/resources")
    @login_required
    def resources_page():
        farm = get_user_farm(get_current_user()["id"])
        from services.market_service import haversine_distance_km
        lat = farm.get("latitude") if farm else None
        lon = farm.get("longitude") if farm else None
        category = request.args.get("category", "ALL").upper()
        rows = get_db().execute("SELECT * FROM resources ORDER BY id DESC").fetchall()
        resources = []
        for row in rows:
            item = dict(row)
            if category != "ALL" and item['category'] != category:
                continue
            item['distance_km'] = haversine_distance_km(lat, lon, item['latitude'], item['longitude']) if None not in (lat, lon, item['latitude'], item['longitude']) else None
            item['items'] = []
            item['directions_url'] = f"https://www.openstreetmap.org/?mlat={item['latitude']}&mlon={item['longitude']}" if item['latitude'] is not None else "https://www.openstreetmap.org/"
            resources.append(item)
        return render_template('resources.html', resources=resources, farm_lat=lat, farm_lon=lon,
                               active_category=category, total_count=len(resources))

    @app.route("/add-resource", methods=["POST"])
    @login_required
    def add_custom_resource():
        name = request.form.get('name', '').strip()
        try:
            lat = float(request.form.get('latitude', ''))
            lon = float(request.form.get('longitude', ''))
            if not name or not is_valid_coordinates(lat, lon):
                raise ValueError
        except (TypeError, ValueError):
            return render_template('error.html', message='Provide a resource name and valid coordinates.'), 400
        get_db().execute("INSERT INTO resources (name, category, seller_name, address, district, state, latitude, longitude, contact_phone, is_seller_listed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
            (name, request.form.get('category', 'OTHER'), request.form.get('seller_name', ''), request.form.get('address', ''), request.form.get('district', ''), request.form.get('state', ''), lat, lon, request.form.get('contact_phone', '')))
        get_db().commit()
        flash('Community listing saved. Availability and prices are not verified.', 'success')
        return redirect(url_for('resources_page'))

    # ==========================================
    # MARKET INTELLIGENCE & SELL PLANNER
    # ==========================================

    @app.route("/market")
    @login_required
    def market_page():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        cycle = get_latest_cycle(farm["id"]) if farm else None
        commodity = (request.args.get("commodity") or (cycle.get("crop_name") if cycle else "Wheat")).strip()

        lat = float(farm["latitude"]) if farm and farm["latitude"] else None
        lon = float(farm["longitude"]) if farm and farm["longitude"] else None

        market_data = get_market_prices_for_commodity(commodity, lat, lon, state=request.args.get("state", ""), district=request.args.get("district", ""), market=request.args.get("market", ""))
        forecast = generate_price_forecast(commodity)
        commodities = get_all_commodities()

        return render_template(
            "market.html",
            commodity=commodity,
            market_data=market_data,
            forecast=forecast, forecast_data=forecast, all_commodities=commodities, selected_commodity=commodity,
            commodities=commodities,
            farm=farm,
        )

    @app.route("/sell-planner", methods=["GET", "POST"])
    @login_required
    def sell_planner_page():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        cycle = get_latest_cycle(farm["id"]) if farm else None
        default_crop = cycle.get("crop_name", "Wheat") if cycle else "Wheat"

        commodity = (request.form.get("commodity") or request.args.get("commodity") or default_crop).strip()
        quantity_qtl = float(request.form.get("quantity_qtl", 25.0))
        transport_rate = float(request.form.get("transport_rate", 3.0))  # Rs per qtl per km

        lat = float(farm["latitude"]) if farm and farm["latitude"] else 18.5204
        lon = float(farm["longitude"]) if farm and farm["longitude"] else 73.8567

        market_data = get_market_prices_for_commodity(commodity, lat, lon)
        forecast = generate_price_forecast(commodity)

        # Calculate net returns for each mandi
        mandis_with_economics = []
        for m in market_data.get("mandis", []):
            dist = float(m.get("distance_km", 20.0))
            price_qtl = float(m.get("modal_price", 2200))
            gross_rev = quantity_qtl * price_qtl
            trans_cost = quantity_qtl * dist * transport_rate
            net_rev = gross_rev - trans_cost
            m_copy = dict(m)
            m_copy["gross_revenue"] = round(gross_rev)
            m_copy["transport_cost"] = round(trans_cost)
            m_copy["net_revenue"] = round(net_rev)
            mandis_with_economics.append(m_copy)

        mandis_with_economics.sort(key=lambda x: x["net_revenue"], reverse=True)

        return render_template(
            "sell_planner.html",
            commodity=commodity,
            quantity_qtl=quantity_qtl,
            transport_rate=transport_rate,
            mandis=mandis_with_economics,
            forecast=forecast,
            farm=farm,
            commodities=get_all_commodities(),
        )

    @app.route("/profit-planner", methods=["GET", "POST"])
    @login_required
    def profit_planner_page():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        cycle = get_latest_cycle(farm["id"]) if farm else None
        default_crop = cycle.get("crop_name", "Wheat") if cycle else "Wheat"

        crop = (request.form.get("crop") or request.args.get("crop") or default_crop).strip()
        area = float(request.form.get("area") or (farm.get("area", 2.0) if farm else 2.0))

        profit_data = calculate_crop_profit_potential(
            crop_name=crop,
            farm_area=area,
            farm_lat=farm.get("latitude") if farm else None,
            farm_lon=farm.get("longitude") if farm else None,
        )

        return render_template(
            "profit_planner.html",
            crop=crop,
            area=area,
            profit_data=profit_data,
            all_crops=get_all_supported_crops(), available_crops=get_all_supported_crops(), selected_crop=crop, farm_area=area, area_unit=farm.get("area_unit", "acre") if farm else "acre",
            farm=farm,
        )

    # ==========================================
    # EXPENSES & REALIZED SALES
    # ==========================================

    @app.route("/expenses")
    @login_required
    def expenses_page():
        farm = get_user_farm(get_current_user()["id"])
        if not farm:
            flash("Set up your farm profile to record farm finances.", "warning")
            return redirect(url_for("farm_setup"))

        expenses = [dict(r) for r in get_db().execute(
            "SELECT * FROM farm_expenses WHERE farm_id = ? ORDER BY date DESC",
            (farm["id"],),
        ).fetchall()]

        sales = [dict(r) for r in get_db().execute(
            "SELECT * FROM sales WHERE farm_id = ? ORDER BY sale_date DESC",
            (farm["id"],),
        ).fetchall()]

        financials = aggregate_farm_financials(expenses, sales)

        return render_template(
            "expenses.html",
            expenses=expenses,
            sales=sales,
            financials=financials,
            farm=farm,
            today=date.today().isoformat(), today_str=date.today().isoformat(),
        )

    @app.route("/add-expense", methods=["POST"])
    @login_required
    def add_expense():
        farm = get_user_farm(get_current_user()["id"])
        if not farm:
            return redirect(url_for("farm_setup"))

        category = (request.form.get("category") or "Other").strip()
        item_name = (request.form.get("vendor") or request.form.get("item_name") or "").strip()
        try:
            amount = float(request.form.get("amount", 0.0))
            if not math.isfinite(amount) or amount < 0:
                raise ValueError
            date.fromisoformat(request.form.get('date') or request.form.get('expense_date') or date.today().isoformat())
        except ValueError:
            return render_template('error.html', message='Enter a nonnegative amount and valid date.'), 400
        expense_date = (request.form.get("date") or request.form.get("expense_date") or date.today().isoformat()).strip()
        notes = (request.form.get("notes") or "").strip()

        if amount > 0:
            get_db().execute(
                """
                INSERT INTO farm_expenses (farm_id, category, vendor, amount, date, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (farm["id"], category, item_name, amount, expense_date, notes),
            )
            get_db().commit()
            flash(f"Expense of ₹{amount:,.0f} recorded under {category}.", "success")
        return redirect(url_for("expenses_page"))

    @app.route("/add-sale", methods=["POST"])
    @login_required
    def add_sale():
        farm = get_user_farm(get_current_user()["id"])
        if not farm:
            return redirect(url_for("farm_setup"))

        crop_name = (request.form.get("commodity") or request.form.get("crop_name") or "Wheat").strip()
        quantity_kg = float(request.form.get("quantity_sold", request.form.get("quantity_kg", 0.0)))
        price_per_kg = float(request.form.get("price_per_unit", request.form.get("price_per_kg", 0.0)))
        mandi_name = (request.form.get("market_name") or request.form.get("mandi_name") or "").strip()
        sale_date = (request.form.get("sale_date") or date.today().isoformat()).strip()
        buyer_type = (request.form.get("buyer_type") or "APMC Mandi").strip()
        notes = (request.form.get("notes") or "").strip()

        total_rev = quantity_kg * price_per_kg
        if not all(math.isfinite(v) and v >= 0 for v in (quantity_kg, price_per_kg, total_rev)):
            return render_template('error.html', message='Enter nonnegative finite sale values.'), 400
        if total_rev > 0:
            get_db().execute(
                """
                INSERT INTO sales (farm_id, commodity, quantity_sold, price_per_unit, total_amount, market_name, sale_date, buyer_name, notes, unit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (farm["id"], crop_name, quantity_kg, price_per_kg, total_rev, mandi_name, sale_date, buyer_type, notes, request.form.get("unit", "kg")),
            )
            get_db().commit()
            flash(f"Harvest sale realized! Revenue of ₹{total_rev:,.0f} recorded.", "success")
        return redirect(url_for("expenses_page"))

    # ==========================================
    # DATA TRANSPARENCY, NOTIFICATIONS & SETTINGS
    # ==========================================

    @app.route("/data-transparency")
    def data_transparency_page():
        return render_template("data_transparency.html")

    @app.route("/notifications")
    @login_required
    def notifications_page():
        user = get_current_user()
        notifs = get_user_notifications(user["id"], get_db())
        return render_template("notifications.html", notifications=notifs)

    @app.route("/notifications/<int:notification_id>/read", methods=["POST"])
    @login_required
    def mark_notification_read_route(notification_id):
        mark_notification_as_read(notification_id, get_db())
        return redirect(url_for("notifications_page"))

    @app.route("/notifications/mark-all-read", methods=["POST"])
    @login_required
    def mark_all_notifications_read():
        mark_all_notifications_as_read(get_current_user()["id"], get_db())
        flash("All notifications marked as read.", "info")
        return redirect(url_for("notifications_page"))

    @app.route("/settings")
    @login_required
    def settings_page():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        return render_template("settings.html", user=user, farm=farm)

    @app.route("/settings/update-profile", methods=["POST"])
    @login_required
    def update_profile():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        name = (request.form.get("name") or user["name"]).strip()
        risk_pref = (request.form.get("risk_preference") or "Balanced").strip()

        get_db().execute("UPDATE users SET name = ? WHERE id = ?", (name, user["id"]))
        if farm:
            get_db().execute("UPDATE farms SET risk_preference = ? WHERE id = ?", (risk_pref, farm["id"]))
        get_db().commit()
        flash("Profile settings updated successfully.", "success")
        return redirect(url_for("settings_page"))

    # ==========================================
    # ADVANCED ANALYTICS, WHAT-IF & DOSSIER REPORT
    # ==========================================

    @app.route("/history")
    @login_required
    def history_page():
        farm = get_user_farm(get_current_user()["id"])
        farm_id = farm["id"] if farm else None
        return render_template("history.html", recommendations=get_db().execute(
            "SELECT * FROM crop_recommendations WHERE farm_id = ? ORDER BY id DESC", (farm_id,)
        ).fetchall(), cycles=get_db().execute(
            "SELECT * FROM crop_cycles WHERE farm_id = ? ORDER BY id DESC", (farm_id,)
        ).fetchall())

    @app.route("/what-if", methods=["GET", "POST"])
    @login_required
    def what_if_page():
        farm = get_user_farm(get_current_user()["id"])
        soil = get_latest_soil_record(farm["id"]) if farm else None
        result = None
        values = {}

        if request.method == "POST":
            try:
                values = {
                    "nitrogen": float(request.form.get("nitrogen", (soil or {}).get("nitrogen", 70))),
                    "phosphorus": float(request.form.get("phosphorus", (soil or {}).get("phosphorus", 40))),
                    "potassium": float(request.form.get("potassium", (soil or {}).get("potassium", 40))),
                    "ph": float(request.form.get("ph", (soil or {}).get("ph", 6.5))),
                    "temperature": float(request.form.get("temperature", 26.0)),
                    "humidity": float(request.form.get("humidity", 65.0)),
                    "rainfall": float(request.form.get("rainfall", 120.0)),
                }
            except (TypeError, ValueError):
                flash("Enter valid numeric conditions for simulation.", "warning")
            else:
                pred = predict_crop(values)
                result = {
                    "prediction": pred,
                    "dataset_fit": compare_crop_dataset_fit(values)[:3],
                    "explanation": build_explanation(pred, values),
                }

        return render_template("what_if.html", values=values or soil or {}, result=result)

    @app.route("/compare-crops", methods=["GET", "POST"])
    @login_required
    def compare_crops_page():
        crops = get_all_supported_crops()
        farm = get_user_farm(get_current_user()["id"])
        soil = get_latest_soil_record(farm["id"]) if farm else None
        results = []
        values = {}

        if request.method == "POST":
            selected = request.form.getlist("crop")
            try:
                values = {
                    "nitrogen": float(request.form.get("nitrogen", (soil or {}).get("nitrogen", 70))),
                    "phosphorus": float(request.form.get("phosphorus", (soil or {}).get("phosphorus", 40))),
                    "potassium": float(request.form.get("potassium", (soil or {}).get("potassium", 40))),
                    "ph": float(request.form.get("ph", (soil or {}).get("ph", 6.5))),
                    "temperature": float(request.form.get("temperature", 26.0)),
                    "humidity": float(request.form.get("humidity", 65.0)),
                    "rainfall": float(request.form.get("rainfall", 120.0)),
                }
            except (TypeError, ValueError):
                flash("Enter all 7 numeric conditions before comparing crops.", "warning")
            else:
                if not 2 <= len(selected) <= 3:
                    flash("Select 2 or 3 crops to compare.", "warning")
                else:
                    results = compare_crop_dataset_fit(values, selected)

        return render_template("compare_crops.html", crops=crops, results=results, values=values or soil or {})

    @app.route("/ml-analytics")
    @login_required
    def ml_analytics_page():
        metrics = get_model_evaluation_metrics()
        return render_template("ml_analytics.html", metrics=metrics)

    @app.route("/risk-analysis")
    @login_required
    def risk_analysis_page():
        farm = get_user_farm(get_current_user()["id"])
        soil = get_latest_soil_record(farm["id"]) if farm else None
        weather = get_latest_weather(farm["id"]) if farm else None
        cycle = get_latest_cycle(farm["id"]) if farm else None
        analysis = analyze_farm_risk(soil, weather, cycle)
        return render_template("risk_analysis.html", farm=farm, soil=soil, weather=weather, cycle=cycle, analysis=analysis)

    @app.route("/weather")
    @login_required
    def weather_page():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        weather = None
        cycle = get_latest_cycle(farm["id"]) if farm else None

        if farm and farm.get("latitude") and farm.get("longitude"):
            try:
                weather = fetch_weather_data(float(farm["latitude"]), float(farm["longitude"]))
                current = weather["current"]
                get_db().execute(
                    """
                    INSERT INTO weather_records (farm_id, temperature, humidity, precipitation, rain_probability, wind_speed, forecast_date, raw_payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (farm["id"], current.get("temperature"), current.get("humidity"), current.get("precipitation"), current.get("rain_probability"), current.get("wind_speed"), date.today().isoformat(), json.dumps(weather)),
                )
                get_db().commit()
            except Exception:
                cached = get_latest_weather(farm['id'])
                if cached and cached.get('raw_payload'):
                    weather = json.loads(cached['raw_payload'])
                    weather['is_stale'] = True
                    weather['is_cached'] = True
                else:
                    weather = None

        weather_analysis = analyze_forecast(weather.get("forecast", []) if weather else [], cycle.get("crop_name", "") if cycle else "", cycle.get("current_stage", "") if cycle else "")
        return render_template("weather.html", farm=farm, weather=weather, weather_analysis=weather_analysis, today=date.today().isoformat())

    @app.route("/report")
    @login_required
    def farm_report_page():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        if not farm:
            flash("Set up your farm profile to view the Farm Dossier Report.", "warning")
            return redirect(url_for("farm_setup"))

        dossier = generate_comprehensive_farm_report(
            farmer=user,
            farm=farm,
            soil=get_latest_soil_record(farm["id"]) or {},
            crop_cycle=get_latest_cycle(farm["id"]),
            weather=get_latest_weather(farm["id"]) or {},
            activities=[dict(r) for r in get_db().execute("SELECT * FROM farm_activities WHERE farm_id = ? ORDER BY due_date ASC", (farm["id"],)).fetchall()],
            disease_reports=[dict(r) for r in get_db().execute("SELECT * FROM disease_reports WHERE farm_id = ? ORDER BY id DESC", (farm["id"],)).fetchall()],
            expenses=[dict(r) for r in get_db().execute("SELECT * FROM farm_expenses WHERE farm_id = ? ORDER BY date DESC", (farm["id"],)).fetchall()],
            sales=[dict(r) for r in get_db().execute("SELECT * FROM sales WHERE farm_id = ? ORDER BY sale_date DESC", (farm["id"],)).fetchall()],
        )

        return render_template(
            "farm_report.html",
            farm=farm,
            dossier=dossier,
            soil=get_latest_soil_record(farm["id"]),
            cycle=get_latest_cycle(farm["id"]),
            weather=get_latest_weather(farm["id"]),
            activities=dossier.get("activities", []),
            recommendation=get_latest_recommendation(farm["id"]),
            lifecycle=dossier.get("lifecycle", {}),
            forecast_days=[],
            advisories=dossier.get("expert_advisories", []),
            risk=dossier.get("risk", {}),
        )

    @app.route("/research")
    def research_page():
        return render_template("research.html")

    # ==========================================
    # JSON APIs
    # ==========================================

    @app.route("/api/reverse-geocode", methods=["POST"])
    @login_required
    def api_reverse_geocode():
        data = request.get_json(silent=True) or {}
        lat = data.get("latitude")
        lon = data.get("longitude")
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            if not is_valid_coordinates(lat_f, lon_f):
                return jsonify({"success": False, "message": "Coordinates out of bounds."}), 400
            loc = reverse_geocode(lat_f, lon_f)
            return jsonify({"success": True, "location": loc})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 400

    @app.route("/api/location", methods=["POST"])
    @login_required
    def api_location():
        payload = request.get_json(silent=True) or {}
        lat = payload.get("latitude")
        lon = payload.get("longitude")
        user = get_current_user()
        farm = get_user_farm(user["id"])
        if not farm:
            return jsonify({"success": False, "message": "Create a farm before storing coordinates."}), 400
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            if not is_valid_coordinates(lat_f, lon_f):
                raise ValueError
        except Exception:
            return jsonify({"success": False, "message": "Invalid coordinates."}), 400

        get_db().execute("UPDATE farms SET latitude = ?, longitude = ? WHERE id = ?", (lat_f, lon_f, farm["id"]))
        get_db().commit()
        return jsonify({"success": True, "latitude": lat_f, "longitude": lon_f})

    @app.route("/api/weather")
    @login_required
    def api_weather():
        user = get_current_user()
        farm = get_user_farm(user["id"])
        if not farm:
            return jsonify({"success": False, "message": "No farm profile found."}), 400
        lat = farm.get("latitude")
        lon = farm.get("longitude")
        if lat is None or lon is None:
            return jsonify({"success": False, "message": "Set farm coordinates first."}), 400
        try:
            w_data = fetch_weather_data(float(lat), float(lon))
            return jsonify({"success": True, "weather": w_data})
        except Exception as exc:
            return jsonify({"success": False, "message": str(exc)}), 400

    @app.route("/api/recommend-crop", methods=["POST"])
    @login_required
    def api_recommend_crop():
        data = request.get_json(silent=True) or {}
        values = {
            "nitrogen": float(data.get("nitrogen", 70)),
            "phosphorus": float(data.get("phosphorus", 40)),
            "potassium": float(data.get("potassium", 40)),
            "ph": float(data.get("ph", 6.5)),
            "temperature": float(data.get("temperature", 26.0)),
            "humidity": float(data.get("humidity", 65.0)),
            "rainfall": float(data.get("rainfall", 120.0)),
        }
        result = predict_crop(values)
        explanation = build_explanation(result, values)
        return jsonify({"success": True, "result": result, "explanation": explanation})

    # ==========================================
    # ERROR HANDLERS
    # ==========================================

    @app.errorhandler(404)
    def handle_404(_):
        return render_template("error.html", message="The requested page could not be found."), 404

    @app.errorhandler(500)
    def handle_500(_):
        return render_template("error.html", message="An unexpected server error occurred."), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
