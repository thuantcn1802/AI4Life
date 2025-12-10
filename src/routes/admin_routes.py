# routes/admin_routes.py
from flask import Blueprint, render_template, request, redirect, url_for
from firebase_connect import db
from routes.permission import require_role

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/")
@require_role("admin")
def admin_dashboard():
    # có thể thêm các thống kê ở đây
    # ví dụ: tổng users, total doctors pending
    users_ref = db.collection("users")
    total_users = len(users_ref.get())
    pending_doctors = []
    for doc in db.collection("users")\
                .where("role","==","doctor")\
                .where("verified_by_admin","==", False)\
                .stream():
            
        d = doc.to_dict()
        d["uid"] = doc.id   # ✅ ADD UID VÀO DATA
        pending_doctors.append(d)    
    return render_template("admin_dashboard.html", total_users=total_users, pending_doctors=pending_doctors)

@admin_bp.route("/users")
@require_role("admin")
def admin_users():
    users = [doc.to_dict() for doc in db.collection("users").stream()]
    return render_template("admin_users.html", users=users)

@admin_bp.route("/verify_doctor", methods=["POST"])
@require_role("admin")
def verify_doctor():
    uid = request.form.get("uid")
    if not uid:
        return "uid required", 400
    db.collection("users").document(uid).update({"verified_by_admin": True})
    return redirect(url_for("admin.admin_dashboard"))
