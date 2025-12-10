# firebase_connect.py  — chỉnh sửa/append
import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
import requests   # mới

base_dir = os.path.dirname(os.path.abspath(__file__))
key_path = os.path.join(base_dir, "serviceAccountKey.json")

# --- Nếu đặt serviceAccountKey ở chỗ khác, sửa đường dẫn phía trên ---
cred = credentials.Certificate(key_path)
firebase_admin.initialize_app(cred)

db = firestore.client()

# -------- Firebase Auth REST usage (client sign-in) ----------
# IMPORTANT: Thay bằng API key web của Firebase (Project settings > Web API Key)
API_KEY = os.environ.get("FIREBASE_API_KEY")

def sign_in_with_email_and_password(email: str, password: str):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    r = requests.post(url, json=payload)
    return r.json()

def verify_id_token(id_token: str):
    """
    Dùng firebase_admin để verify token. Trả về decoded token nếu hợp lệ, else None.
    """
    try:
        decoded = auth.verify_id_token(id_token)
        return decoded
    except Exception:
        return None

# giữ hàm hiện tại
def get_disease(code):
    doc = db.collection("skin_cancer").document(code).get()
    return doc.to_dict() if doc.exists else None
