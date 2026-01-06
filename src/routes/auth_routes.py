from flask import Blueprint, render_template, request, session, redirect, url_for
from functools import wraps
from firebase_connect import db  # đảm bảo firebase_connect.py export 'db' như đã hướng dẫn trước
from firebase_connect import (
    sign_in_with_email_and_password,
    verify_id_token
)
from firebase_admin import auth, firestore


auth_bp = Blueprint("auth", __name__)


# ----- Middleware Login -----
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        print("--- DEBUG: Middleware Start ---") # Log 1
        id_token = session.get("idToken")
        
        if not id_token:
            print("--- DEBUG: No idToken in session ---") # Log 2
            return redirect(url_for("auth.login"))
            
        print(f"--- DEBUG: Found Token: {id_token[:10]}... ---") # Log 3
        
        try:
            # Thêm try/except để bắt lỗi từ Firebase verify
            user = verify_id_token(id_token)
            if not user:
                print("--- DEBUG: verify_id_token returned None/False ---") # Log 4
                session.clear()
                return redirect(url_for("auth.login"))
            
            print("--- DEBUG: User verified OK ---") # Log 5
            return f(*args, **kwargs)
            
        except Exception as e:
            print(f"--- DEBUG: verify_id_token CRASHED: {e} ---") # Log 6
            session.clear()
            return redirect(url_for("auth.login"))
            
    return decorated

# ----- Login -----
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip()
        password = request.form.get("password","").strip()

        res = sign_in_with_email_and_password(email, password)

        # login fail
        if "idToken" not in res:
            err = res.get("error",{}).get("message","Đăng nhập thất bại")
            return render_template("login.html", error=err)

        # login ok
        session["idToken"] = res["idToken"]
        session["email"] = res.get("email")

        uid = res.get("localId")
        
        session["uid"] = uid 

        # load user profile
        user_doc = db.collection("users").document(uid).get()

        if not user_doc.exists:
            # Nếu user chưa có trong database, có thể tự tạo nhanh hoặc báo lỗi
            # Ở đây ta báo lỗi như cũ
            session.clear()
            return render_template("login.html", error="Tài khoản chưa có profile")

        profile = user_doc.to_dict()
        role = profile.get("role","user")

        # Lưu role vào session
        session["role"] = role

        # redirect theo role
        if role == "admin":
            return redirect("/admin")
        elif role == "doctor":
            return redirect("/")
        else:
            return redirect("/") 

    return render_template("login.html")


# trong routes/auth_routes.py (chỉ thay phần register)

@auth_bp.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email","").strip()
        password = request.form.get("password","").strip()
        role = request.form.get("role","user").strip()  # 'user' hoặc 'doctor'

        if not email or not password or len(password) < 6:
            return render_template("register.html", error="Email và mật khẩu >= 6 ký tự")

        try:
            # tạo user bằng admin SDK
            user = auth.create_user(email=email, password=password)

            # lưu document users/{uid}
            db.collection("users").document(user.uid).set({
                "email": email,
                "role": role,
                # Nếu muốn, lưu flag xác minh cho bác sĩ:
                "verified_by_admin": False if role == "doctor" else True,
                "created_at": firestore.SERVER_TIMESTAMP
            })

            # sau khi tạo, redirect đến login
            return redirect(url_for("auth.login"))

        except Exception as e:
            # trả lỗi hợp lý (nên parse message nếu muốn)
            return render_template("register.html", error=str(e))

    return render_template("register.html")


# ----- Logout -----
@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
