# create_admin.py (da chay 1 lan de tao tai khoan admin)
from firebase_admin import auth
from firebase_connect import db

email = "admin@gmail.com"   # <-- THAY bằng email admin thật
password = "admin123"  # <-- THAY bằng mật khẩu an toàn

try:
    user = auth.create_user(email=email, password=password)
    uid = user.uid
    print("Created admin uid:", uid)
    # lưu vào firestore
    db.collection("users").document(uid).set({
        "email": email,
        "role": "admin",
        "verified_by_admin": True
    })
    print("Admin profile saved to Firestore.")
except Exception as e:
    print("Error:", e)
