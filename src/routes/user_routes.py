from flask import Blueprint, render_template
from routes.permission import require_role

user_bp = Blueprint("user", __name__)

@user_bp.route("/user/dashboard")
@require_role(["user","doctor"])
def user_dashboard():
    return render_template("user_dashboard.html")
