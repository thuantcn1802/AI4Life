from flask import Blueprint, render_template
from routes.permission import require_role

doctor_bp = Blueprint("doctor", __name__)

@doctor_bp.route("/doctor/dashboard")
@require_role("doctor")
def doctor_dashboard():
    return render_template("doctor_dashboard.html")
