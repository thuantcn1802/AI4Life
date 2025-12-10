from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from assistant import generate_reply, detect_disease_in_text
from knowledge import search_similar_question, save_knowledge
from groq_service import ask_groq
import numpy as np
import cv2, os
from firebase_connect import verify_id_token, sign_in_with_email_and_password
from functools import wraps
from routes.auth_routes import auth_bp,login_required
from routes.detect_routes import detect_bp
from routes.admin_routes import admin_bp
from routes.user_routes import user_bp
from routes.doctor_routes import doctor_bp
from dotenv import load_dotenv

load_dotenv()

# Định nghĩa đường dẫn tới thư mục templates (nằm ngoài thư mục src)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Khởi tạo Flask, chỉ rõ đường dẫn template_folder
app = Flask(__name__, template_folder=TEMPLATES_DIR)

# Cấu hình static đúng với vị trí gốc (nếu static nằm cạnh templates)
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.static_folder = STATIC_DIR
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
app.register_blueprint(auth_bp)
app.register_blueprint(detect_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)
app.register_blueprint(doctor_bp)

UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER



@app.route("/")
def home():
    return render_template("index.html")



@app.route("/chatbox")
@login_required
def chat_ui():
    return render_template("chat.html")

@app.route("/chat", methods=["POST"])
def chat_api():
    user_msg = request.json.get("message", "")

    # 1) Kiểm tra DB có câu hỏi tương tự
    cached_answer = search_similar_question(user_msg)
    if cached_answer:
        return jsonify({"reply": cached_answer})

    # 2) Kiểm tra có liên quan đến 9 bệnh da không
    disease_code = detect_disease_in_text(user_msg)
    if disease_code:
        answer = generate_reply(user_msg)
        save_knowledge(user_msg, answer)
        return jsonify({"reply": answer})

    # 3) Gọi Groq nếu không có trong DB và không phải bệnh học
    ai_reply = ask_groq(user_msg)

    # 4) Lưu tri thức để bot tự học
    save_knowledge(user_msg, ai_reply)

    return jsonify({"reply": ai_reply})


if __name__ == "__main__":
    app.run(debug=True) 
