# routes/admin_routes.py
from flask import Blueprint, render_template, request, redirect, url_for
from firebase_connect import db
# IMPORT QUAN TRỌNG: cần firestore để lấy SERVER_TIMESTAMP
from firebase_admin import auth, firestore 
from routes.permission import require_role

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/")
@require_role("admin")
def admin_dashboard():
    # Lấy toàn bộ user từ Firestore
    users_ref = db.collection("users").stream()
    
    all_users = []
    for doc in users_ref:
        u = doc.to_dict()
        u["uid"] = doc.id
        
        # Xử lý hiển thị mặc định nếu thiếu trường
        if "role" not in u: u["role"] = "user"
        if "verified_by_admin" not in u: u["verified_by_admin"] = False
        
        all_users.append(u)

    # Sắp xếp: Doctor chưa duyệt lên đầu, sau đó theo tên
    all_users.sort(key=lambda x: (x.get("verified_by_admin", True), x.get("email", "")))

    return render_template("admin_dashboard.html", users=all_users)

# --- CREATE USER (Đã sửa created_at) ---
@admin_bp.route("/create_user", methods=["POST"])
@require_role("admin")
def create_user():
    email = request.form.get("email")
    password = request.form.get("password")
    role = request.form.get("role", "user")
    
    try:
        # 1. Tạo User bên Authentication
        user_record = auth.create_user(email=email, password=password)
        
        # 2. Tạo User Profile bên Firestore
        # SỬA Ở ĐÂY: Dùng firestore.SERVER_TIMESTAMP giống code register của bạn
        db.collection("users").document(user_record.uid).set({
            "email": email,
            "role": role,
            "verified_by_admin": False if role == "doctor" else True,
            "created_at": firestore.SERVER_TIMESTAMP 
        })
        
    except Exception as e:
        print("Error creating user:", e)
        
    return redirect(url_for("admin.admin_dashboard"))

# --- EDIT USER ---
@admin_bp.route("/edit_user", methods=["POST"])
@require_role("admin")
def edit_user():
    uid = request.form.get("uid")
    role = request.form.get("role")
    verified = True if request.form.get("verified_by_admin") else False
    
    try:
        db.collection("users").document(uid).update({
            "role": role,
            "verified_by_admin": verified
        })
    except Exception as e:
        print("Error updating user:", e)

    return redirect(url_for("admin.admin_dashboard"))

# --- DELETE USER (Đã tách try/except) ---
@admin_bp.route("/delete_user", methods=["POST"])
@require_role("admin")
def delete_user():
    uid = request.form.get("uid")
    
    if not uid:
        return redirect(url_for("admin.admin_dashboard"))

    # 1. Xóa dữ liệu Firestore trước
    try:
        db.collection("users").document(uid).delete()
    except Exception as e:
        print(f"Lỗi xóa Firestore: {e}")

    # 2. Xóa tài khoản Auth sau
    try:
        auth.delete_user(uid)
    except Exception as e:
        print(f"Lỗi xóa Auth: {e}")
        
    return redirect(url_for("admin.admin_dashboard"))

# --- VERIFY QUICK ACTION ---
@admin_bp.route("/verify_doctor_quick", methods=["POST"])
@require_role("admin")
def verify_doctor_quick():
    uid = request.form.get("uid")
    if uid:
        try:
            db.collection("users").document(uid).update({"verified_by_admin": True})
        except Exception:
            pass
    return redirect(url_for("admin.admin_dashboard"))