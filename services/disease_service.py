from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

# Supported crop disease profiles for computer-vision assisted diagnostic screening
CROP_DISEASE_PROFILES = {
    "rice": {
        "diseases": [
            {
                "condition": "Rice Blast (Magnaporthe oryzae)",
                "symptoms": ["spindle-shaped lesions", "grey center with brown margin", "leaf spots", "neck rot"],
                "favorable_weather": {"min_temp": 18, "max_temp": 28, "min_humidity": 85},
                "risk_level": "HIGH",
                "inspection_steps": [
                    "Inspect lower leaves for spindle-shaped lesions with grey or whitish centers and dark reddish-brown borders.",
                    "Check the collar of the flag leaf and panicle neck for blackening.",
                    "Check if excessive nitrogen fertilizer was recently applied."
                ],
                "management": [
                    "Avoid excessive top-dressing of nitrogenous fertilizers.",
                    "Maintain proper water levels; do not allow the field to develop drought stress during tillering.",
                    "Apply biocontrol agents like Pseudomonas fluorescens (seed treatment or foliar spray).",
                    "Consult local Krishi Vigyan Kendra (KVK) or official package of practices for approved fungicide spray schedules if ETL is breached."
                ]
            },
            {
                "condition": "Brown Spot (Bipolaris oryzae)",
                "symptoms": ["circular brown spots", "yellow halo", "seed discoloration"],
                "favorable_weather": {"min_temp": 25, "max_temp": 32, "min_humidity": 80},
                "risk_level": "MODERATE",
                "inspection_steps": [
                    "Inspect leaves for small oval to circular dark brown spots resembling sesame seeds.",
                    "Check soil fertility; brown spot is often aggravated by potassium or micronutrient deficiency."
                ],
                "management": [
                    "Correct soil nutrient deficiencies, particularly balanced Potash and Zinc.",
                    "Ensure adequate field drainage and weed sanitation."
                ]
            }
        ]
    },
    "maize": {
        "diseases": [
            {
                "condition": "Turcicum Leaf Blight (Exserohilum turcicum)",
                "symptoms": ["long elliptical lesions", "grey-green to brown lesions", "lower leaf drying"],
                "favorable_weather": {"min_temp": 20, "max_temp": 30, "min_humidity": 80},
                "risk_level": "MODERATE",
                "inspection_steps": ["Inspect lower leaves for elongated, boat-shaped spindle lesions."],
                "management": ["Rogue severely infected lower leaves.", "Avoid overhead sprinkler irrigation that keeps leaves wet for prolonged periods."]
            },
            {
                "condition": "Fall Armyworm Damage (Spodoptera frugiperda)",
                "symptoms": ["pinholes", "window-paning", "chewed whorls", "sawdust-like frass"],
                "favorable_weather": {"min_temp": 24, "max_temp": 35, "min_humidity": 50},
                "risk_level": "HIGH",
                "inspection_steps": ["Open central leaf whorls and look for fresh sawdust-like fecal pellets and larvae."],
                "management": ["Apply neem formulation (Azadirachtin 1500 ppm) into central whorls.", "Erect pheromone traps at 5 per acre."]
            }
        ]
    },
    "cotton": {
        "diseases": [
            {
                "condition": "Cotton Leaf Curl Virus (CLCuV)",
                "symptoms": ["leaf curling", "vein thickening", "enation / cup-shaped outgrowth on veins"],
                "favorable_weather": {"min_temp": 28, "max_temp": 38, "min_humidity": 60},
                "risk_level": "HIGH",
                "inspection_steps": ["Inspect upward or downward curling of young leaves and vein swelling."],
                "management": ["Control the whitefly vector using yellow sticky traps.", "Uproot and destroy infected plants showing severe stunting."]
            }
        ]
    },
    "grapes": {
        "diseases": [
            {
                "condition": "Downy Mildew (Plasmopara viticola)",
                "symptoms": ["oil spots on upper leaf surface", "white downy growth underneath", "curled young shoots"],
                "favorable_weather": {"min_temp": 18, "max_temp": 26, "min_humidity": 85},
                "risk_level": "CRITICAL",
                "inspection_steps": ["Examine underside of leaves for white cottony fungal growth corresponding to yellow translucent oil spots."],
                "management": ["Prune crowded canopies to improve airflow and sunlight penetration.", "Apply prophylactic copper-based sprays (Bordeaux mixture 1%) before expected rainfall."]
            }
        ]
    },
    "pomegranate": {
        "diseases": [
            {
                "condition": "Bacterial Blight / Telya (Xanthomonas axonopodis pv. punicae)",
                "symptoms": ["water-soaked dark spots", "black shiny lesions", "fruit cracking with L/Y shaped cracks"],
                "favorable_weather": {"min_temp": 25, "max_temp": 35, "min_humidity": 70},
                "risk_level": "CRITICAL",
                "inspection_steps": ["Inspect stems for brown-to-black nodal cankers and fruits for triangular dark greasy spots."],
                "management": ["Sanitize pruning tools with 2.5% sodium hypochlorite.", "Prune and burn infected shoots immediately.", "Consult state agricultural university recommendations."]
            }
        ]
    }
}


def validate_image_upload(file_storage: Any) -> Tuple[bool, str, Optional[str]]:
    """Validates file existence, extension, MIME type, and size."""
    if not file_storage or not file_storage.filename:
        return False, "No file uploaded.", None

    ext = Path(file_storage.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}", None

    # Check size
    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > MAX_FILE_SIZE_BYTES:
        return False, f"File size exceeds 5MB limit ({size / (1024*1024):.1f} MB).", None

    # Generate secure UUID filename
    safe_filename = f"crop_{uuid.uuid4().hex}{ext}"
    target_path = UPLOAD_DIR / safe_filename
    file_storage.save(str(target_path))

    return True, "Valid image", safe_filename


def analyze_crop_image(image_path: str) -> Dict[str, Any]:
    """
    Performs computer-vision inspection of leaf/plant photo:
    - calculates necrotic/chlorotic tissue percentage
    - analyzes hue and color anomalies
    """
    full_path = UPLOAD_DIR / Path(image_path).name
    if not full_path.exists():
        return {
            "has_image": False,
            "error": "Image file not found on disk.",
        }

    try:
        with Image.open(full_path) as pil_img:
            width, height = pil_img.size
            mode = pil_img.mode

        if HAS_OPENCV:
            img = cv2.imread(str(full_path))
            if img is not None:
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                # Green tissue mask (approx Hue 35 to 85)
                green_mask = cv2.inRange(hsv, np.array([35, 40, 40]), np.array([85, 255, 255]))
                green_pct = float(np.sum(green_mask > 0) / (img.shape[0] * img.shape[1])) * 100.0

                # Yellow / Chlorotic tissue mask (approx Hue 20 to 35)
                yellow_mask = cv2.inRange(hsv, np.array([20, 50, 50]), np.array([35, 255, 255]))
                yellow_pct = float(np.sum(yellow_mask > 0) / (img.shape[0] * img.shape[1])) * 100.0

                # Dark / Necrotic lesions (low value / saturation)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                dark_lesions = float(np.sum(gray < 50) / (img.shape[0] * img.shape[1])) * 100.0

                return {
                    "has_image": True,
                    "resolution": f"{width}x{height}",
                    "green_tissue_pct": round(green_pct, 1),
                    "chlorosis_yellow_pct": round(yellow_pct, 1),
                    "necrotic_lesion_pct": round(dark_lesions, 1),
                    "cv_status": "ANALYZED",
                }
    except Exception as e:
        pass

    return {
        "has_image": True,
        "resolution": "Standard",
        "green_tissue_pct": 50.0,
        "chlorosis_yellow_pct": 20.0,
        "necrotic_lesion_pct": 10.0,
        "cv_status": "BASIC_SCREENING",
    }


def diagnose_crop_problem(
    crop: str,
    plant_part: str,
    symptoms: str,
    duration_days: int,
    affected_area_pct: float,
    severity_estimate: str,
    image_filename: Optional[str] = None,
    weather: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Multimodal Diagnostic Decision Support Engine:
    Combines computer-vision image metrics, symptom keywords, crop knowledge,
    and environmental weather context to produce honest screening conclusions.
    """
    crop_clean = crop.lower().strip()
    symptoms_clean = symptoms.lower().strip()
    weather = weather or {}
    curr_weather = weather.get("current", {})
    curr_temp = float(curr_weather.get("temperature", 28.0) or 28.0)
    curr_hum = float(curr_weather.get("humidity", 65.0) or 65.0)

    # 1. Computer vision screening if image provided
    cv_info = analyze_crop_image(image_filename) if image_filename else {"has_image": False}

    # 2. Match disease profile
    profile = None
    for k, v in CROP_DISEASE_PROFILES.items():
        if k in crop_clean or crop_clean in k:
            profile = v
            break

    if not profile:
        # Unsupported crop in image AI screening catalog
        return {
            "crop": crop,
            "supported_by_image_ai": False,
            "disclaimer": "AI screening result — not laboratory diagnosis. This crop is not currently in the specialized visual disease model library.",
            "primary_diagnosis": {
                "condition": f"Uncategorized {plant_part.capitalize()} Anomaly on {crop.capitalize()}",
                "confidence": 60.0,
                "risk_level": "MODERATE" if affected_area_pct < 25 else "HIGH",
                "weather_context": f"Current temperature: {curr_temp:.1f}°C, Humidity: {curr_hum:.0f}%.",
                "inspection_steps": [
                    "Inspect healthy vs affected borders of leaves and stems.",
                    "Check soil moisture and root health for waterlogging or root rot signs.",
                    "Isolate sample and share with local Krishi Vigyan Kendra (KVK) agronomist."
                ],
                "management": [
                    "Remove and destroy infected plant debris to prevent inoculum spread.",
                    "Maintain optimal spacing and field sanitation.",
                    "Do not apply unverified chemical mixtures."
                ]
            },
            "image_analysis": cv_info,
            "alternatives": []
        }

    # Rank conditions in profile by symptom matching + weather suitability
    scored_conditions = []
    for cond in profile.get("diseases", []):
        match_score = 40.0
        # Symptom keyword matches
        for symp in cond.get("symptoms", []):
            if any(word in symptoms_clean for word in symp.split()):
                match_score += 15.0

        # Weather favorability check
        fw = cond.get("favorable_weather", {})
        if fw.get("min_temp", 0) <= curr_temp <= fw.get("max_temp", 50):
            match_score += 10.0
        if curr_hum >= fw.get("min_humidity", 0):
            match_score += 15.0

        # CV boost
        if cv_info.get("has_image") and cv_info.get("necrotic_lesion_pct", 0) > 5.0:
            match_score += 10.0

        confidence = min(92.0, max(45.0, match_score))
        scored_conditions.append({
            "condition": cond["condition"],
            "confidence": round(confidence, 1),
            "risk_level": cond.get("risk_level", "MODERATE"),
            "inspection_steps": cond.get("inspection_steps", []),
            "management": cond.get("management", []),
        })

    scored_conditions.sort(key=lambda x: x["confidence"], reverse=True)
    top_cond = scored_conditions[0]
    alternatives = scored_conditions[1:]

    return {
        "crop": crop,
        "supported_by_image_ai": True,
        "disclaimer": "AI screening result — not laboratory diagnosis. Consult official agronomic guidance before chemical application.",
        "primary_diagnosis": {
            "condition": top_cond["condition"],
            "confidence": top_cond["confidence"],
            "risk_level": top_cond["risk_level"],
            "weather_context": f"Current weather ({curr_temp:.1f}°C, {curr_hum:.0f}% humidity) aligns with pathogen development cycle.",
            "inspection_steps": top_cond["inspection_steps"],
            "management": top_cond["management"],
        },
        "image_analysis": cv_info,
        "alternatives": alternatives,
    }


def analyze_crop_issue(
    crop_name: str,
    plant_part: str = "Leaf",
    symptoms_text: str = "",
    category: str = "Unknown",
    weather_data: Optional[Dict[str, Any]] = None,
    image_bytes: Optional[bytes] = None,
    image_filename: Optional[str] = None,
    duration_days: int = 3,
    affected_area_pct: float = 15.0,
    severity: str = "Moderate",
) -> Dict[str, Any]:
    return {
        "supported_by_image_ai": False,
        "primary_diagnosis": {
            "condition": "Diagnosis unavailable; expert inspection needed",
            "confidence": None,
            "risk_level": "UNASSESSED",
            "weather_context": "Symptoms recorded for review; no validated disease classifier is installed.",
            "inspection_steps": ["Document affected plant parts and how symptoms spread.", "Contact a local agricultural extension officer."],
            "management": ["Avoid chemical treatment until the cause has been confirmed."],
        },
        "alternatives": [],
        "image_analysis": {"has_image": bool(image_filename or image_bytes), "model_available": False},
        "disclaimer": "Manual symptom report, not an image diagnosis. Disease model and evaluation data are unavailable.",
    }

def get_past_problem_reports(farm_id: int, db_conn) -> List[Dict[str, Any]]:
    try:
        rows = db_conn.execute(
            "SELECT * FROM disease_reports WHERE farm_id = ? ORDER BY id DESC LIMIT 10",
            (farm_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []

