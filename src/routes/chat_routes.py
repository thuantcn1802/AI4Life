# routes/chat_routes.py
import io
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from routes.auth_routes import login_required
from services.storage_supabase import upload_image_to_supabase
from firebase_connect import db

chat_bp = Blueprint("chat", __name__)

@chat_bp.route("/chat")
@login_required
def chat_ui():
    # Lấy thông tin người dùng hiện tại
    current_uid = session.get("uid")
    
    # Lấy role để frontend biết (ví dụ: User không thể chat với User khác, chỉ Chat với Doctor)
    user_ref = db.collection("users").document(current_uid).get()
    role = user_ref.to_dict().get("role", "user") if user_ref.exists else "user"
    
    # Nếu có tham số doctor_id từ URL (khi click từ danh sách bác sĩ)
    target_id = request.args.get("doctor_id", "")
    
    return render_template("chatbox.html", 
                           current_uid=current_uid, 
                           current_role=role,
                           target_id=target_id)

@chat_bp.route("/api/chat/upload", methods=["POST"])
@login_required
def upload_chat_image():
    """API nhận ảnh từ JS, upload lên Supabase và trả về URL"""
    if 'image' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        # Đọc file thành bytes
        image_bytes = file.read()
        uid = session.get("uid")
        
        # Tái sử dụng hàm upload của bạn (lưu ý: hàm này trả về visit_id và url)
        # Ta chỉ cần URL.
        _, public_url = upload_image_to_supabase(uid, image_bytes)
        
        return jsonify({"image_url": public_url})
        
    except Exception as e:
        print("Chat upload error:", e)
        return jsonify({"error": str(e)}), 500