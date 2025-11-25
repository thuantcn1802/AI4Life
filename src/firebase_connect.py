import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

def get_disease(code):
    doc = db.collection("skin_cancer").document(code).get()
    return doc.to_dict() if doc.exists else None
