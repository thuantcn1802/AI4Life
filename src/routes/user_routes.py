# routes/user_routes.py
from flask import Blueprint, render_template, session, redirect, url_for
from firebase_connect import db
from routes.auth_routes import login_required 

user_bp = Blueprint("user", __name__)

@user_bp.route("/user/doctors")
@login_required
def list_doctors():
    # 1. Lấy thông tin người đang xem để quyết định có hiện nút chat không
    current_uid = session.get("uid")
    
    # Lấy role hiện tại từ Firestore (để chắc chắn đúng quyền mới nhất)
    # (Nếu session lúc login bạn chưa lưu role thì phải query lại như này)
    current_user_doc = db.collection("users").document(current_uid).get()
    if not current_user_doc.exists:
        return redirect("/logout")
        
    current_user_data = current_user_doc.to_dict()
    current_role = current_user_data.get("role", "user")

    # 2. Lấy danh sách bác sĩ (Chỉ lấy bác sĩ ĐÃ ĐƯỢC DUYỆT)
    doctors_ref = db.collection("users")\
        .where("role", "==", "doctor")\
        .where("verified_by_admin", "==", True)\
        .stream()

    doctors = []
    for doc in doctors_ref:
        d = doc.to_dict()
        d["uid"] = doc.id
        
        # Tạo thêm vài thông tin giả lập nếu thiếu (như avatar, chuyên khoa)
        # Để giao diện đẹp hơn
        if "full_name" not in d: d["full_name"] = d.get("email").split("@")[0]
        if "specialty" not in d: d["specialty"] = "General Doctor"
        
        doctors.append(d)

    return render_template("doctors_list.html", 
                           doctors=doctors, 
                           current_role=current_role)