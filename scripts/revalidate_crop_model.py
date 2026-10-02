"""Evaluate the saved model on its documented benchmark split without training."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from services.crop_ml_service import MODEL_PATH, DATASET_PATH, FEATURE_COLUMNS

data = pd.read_csv(DATASET_PATH)
_, x, _, y = train_test_split(data[FEATURE_COLUMNS], data['label'], test_size=.2, random_state=42, stratify=data['label'])
model = joblib.load(MODEL_PATH)
prediction = model.predict(x)
result = {'evaluation': 'Documented benchmark split; not independent field validation',
          'rows': len(data), 'features': list(model.feature_names_in_),
          'accuracy': accuracy_score(y, prediction),
          'macro_precision': precision_score(y, prediction, average='macro'),
          'macro_recall': recall_score(y, prediction, average='macro'),
          'macro_f1': f1_score(y, prediction, average='macro'),
          'labels': list(model.classes_),
          'confusion_matrix': confusion_matrix(y, prediction, labels=model.classes_).tolist()}
Path('artifacts').mkdir(exist_ok=True)
Path('artifacts/model_revalidation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k not in ('labels', 'confusion_matrix')}))
