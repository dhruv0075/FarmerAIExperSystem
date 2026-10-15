
import json
from pathlib import Path
from collections.abc import Mapping

import torch
from torch import nn
from torchvision import models, transforms
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

with open(BASE_DIR / "class_names.json", "r", encoding="utf-8") as class_file:
    CLASS_NAMES = json.load(class_file)

if (
    not isinstance(CLASS_NAMES, list)
    or len(CLASS_NAMES) != 38
    or any(not isinstance(name, str) or not name.strip() for name in CLASS_NAMES)
    or len(set(CLASS_NAMES)) != len(CLASS_NAMES)
):
    raise ValueError("The classifier class mapping must contain 38 unique class names.")

model = models.mobilenet_v3_small(weights=None)
in_features = model.classifier[-1].in_features
model.classifier[-1] = nn.Linear(in_features, len(CLASS_NAMES))
state = torch.load(BASE_DIR / "best_model.pth", map_location=DEVICE, weights_only=True)
if not isinstance(state, Mapping):
    raise ValueError("The classifier checkpoint must contain a state dictionary.")
model.load_state_dict(state, strict=True)
if model.classifier[-1].out_features != len(CLASS_NAMES):
    raise ValueError("The classifier output dimension does not match its class mapping.")
model = model.to(DEVICE)
model.eval()


transform = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ]
)


def predict_raw(image):
    """Return the closed-set top class and its uncalibrated softmax score."""
    if not isinstance(image,Image.Image):
        image=Image.open(image)
    image=image.convert("RGB")
    tensor = transform(image).unsqueeze(0).to(DEVICE)
    with torch.inference_mode():
        outputs = model(tensor)
        probabilities = torch.softmax(outputs, dim=1)[0]
    confidence, index = torch.max(probabilities, dim=0)
    label = CLASS_NAMES[index.item()]
    parts = label.split("___", 1)
    crop = parts[0].replace("_", " ")
    disease = parts[1].replace("_", " ") if len(parts) > 1 else label
    return {
        "crop": crop,
        "predicted_class": label,
        "disease": disease,
        "confidence": round(float(confidence.item()) * 100, 2),
    }


def predict_disease(image):
    prediction = predict_raw(image)
    return {
        "status": "prediction",
        **prediction,
        "message": (
            "This is the model's closest match among its 38 PlantVillage classes, "
            "not a confirmed diagnosis. Its score is uncalibrated, and unfamiliar "
            "field images may be misclassified. Consult a qualified agricultural expert."
        ),
    }