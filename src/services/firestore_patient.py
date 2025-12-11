# services/firestore_patient.py
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# Init Firebase Admin once
if not firebase_admin._apps:
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "serviceAccountKey.json")
    if not os.path.exists(cred_path):
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS not set or file missing: " + cred_path)
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def save_visit_firestore(uid: str, visit_id: str, prediction_data: dict, visit_type: str, image_url: str):
    """
    Save visit metadata under users/{uid}/visits/{visit_id}
    prediction_data: {"class_name":..., "confidence":..., "all_probabilities":[...]}
    """
    doc_ref = db.collection("users").document(uid).collection("visits").document(visit_id)
    payload = {
        "visit_id": visit_id,
        "visit_type": visit_type,
        "image_url": image_url,
        "prediction": prediction_data.get("class_name"),
        "confidence": float(prediction_data.get("confidence", 0)),
        "all_probabilities": [float(x) for x in prediction_data.get("all_probabilities", [])],
        "timestamp": datetime.utcnow().isoformat()
    }
    doc_ref.set(payload)
    return payload

def get_visits_firestore(uid: str):
    col = db.collection("users").document(uid).collection("visits").order_by("timestamp")
    docs = col.stream()
    return [d.to_dict() for d in docs]
