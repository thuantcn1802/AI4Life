from flask import Blueprint, render_template, request, jsonify
from routes.auth_routes import login_required

detect_bp = Blueprint("detect", __name__)

@detect_bp.route("/detect", methods=["GET"])
@login_required
def detect_ui():
    return render_template("detect.html")

@detect_bp.route("/detect_api", methods=["POST"])
@login_required
def detect_api():
    data = request.json
    text = data.get("text", "")

    # Giả sử có hàm detect_disease_in_text để phát hiện bệnh từ văn bản
    disease_code = detect_disease_in_text(text)

    if disease_code:
        return jsonify({"disease_code": disease_code})
    else:
        return jsonify({"disease_code": None})
def detect_disease_in_text(text):
    # Hàm giả lập phát hiện bệnh từ văn bản
    diseases = {
        "eczema": ["eczema", "chàm"],
        "psoriasis": ["psoriasis", "vảy nến"],
        "acne": ["acne", "mụn trứng cá"],
        # Thêm các bệnh khác nếu cần
    }

    for code, keywords in diseases.items():
        for keyword in keywords:
            if keyword.lower() in text.lower():
                return code
    return None