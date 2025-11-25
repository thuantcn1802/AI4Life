from flask import Flask, render_template, request, jsonify
from tensorflow.keras.models import load_model
from assistant import generate_reply, detect_disease_in_text
from knowledge import search_similar_question, save_knowledge
from groq_service import ask_groq
import numpy as np
import cv2, os

# Định nghĩa đường dẫn tới thư mục templates (nằm ngoài thư mục src)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Khởi tạo Flask, chỉ rõ đường dẫn template_folder
app = Flask(__name__, template_folder=TEMPLATES_DIR)

# Cấu hình static đúng với vị trí gốc (nếu static nằm cạnh templates)
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.static_folder = STATIC_DIR

UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER



# Danh sách 9 lớp bệnh theo dataset ISIC
CLASSES = [
    'pigmented benign keratosis',
    'melanoma',
    'vascular lesion',
    'actinic keratosis',
    'squamous cell carcinoma',
    'basal cell carcinoma',
    'seborrheic keratosis',
    'dermatofibroma',
    'nevus'
]

# Phân nhóm nguy cơ y học
HIGH_RISK = {'melanoma', 'squamous cell carcinoma', 'basal cell carcinoma'}
MEDIUM_RISK = {'actinic keratosis', 'vascular lesion'}
LOW_RISK = {'pigmented benign keratosis', 'seborrheic keratosis', 'dermatofibroma', 'nevus'}

# Load model
MODEL_PATH = "../models/best_skin_cancer_model.keras"

models = []
if os.path.exists(MODEL_PATH):
    try:
        model = load_model(MODEL_PATH, compile=False)
        models.append(model)
        print(f"Loaded: {MODEL_PATH}")
    except Exception as e:
        print(f"Error loading {MODEL_PATH}: {e}")
else:
    print(f"Not found: {MODEL_PATH}")

print(f"Total models loaded: {len(models)}")

# Tiền xử lý ảnh
def preprocess_image(image_path, img_size=(224, 224)):
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (img_size[1], img_size[0]))
    img = img.astype("float32") / 255.0
    return np.expand_dims(img, axis=0)

# Dự đoán 1 model
def ensemble_predict(image_path):
    if not models:
        raise ValueError("No model loaded.")
    img = preprocess_image(image_path)
    pred = models[0].predict(img, verbose=0)[0]
    top_idx = np.argmax(pred)
    label = CLASSES[top_idx]
    confidence = float(pred[top_idx])
    return label, confidence

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("file")
        if file:
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], file.filename))

            image_url = f"uploads/{file.filename}"

            label, prob = ensemble_predict(os.path.join(app.config["UPLOAD_FOLDER"], file.filename))

            if label in HIGH_RISK:
                risk = "Cao (Ung thư ác tính)"
            elif label in MEDIUM_RISK:
                risk = "Trung bình (Tổn thương tiền ung thư)"
            else:
                risk = "Thấp (Tổn thương lành tính)"

            return render_template(
                "result.html",
                file_path=image_url,
                pred_label=label,
                probability=round(prob, 3),
                risk_level=risk
            )
    return render_template("index.html")

@app.route("/chatbox")
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

@app.route("/predict", methods=["POST"])
def predict_api():
    file = request.files.get("file")

    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    # lưu file
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)

    # dự đoán
    label, prob = ensemble_predict(file_path)

    # phân mức nguy cơ
    if label in HIGH_RISK:
        risk = "Cao (Ung thư ác tính)"
    elif label in MEDIUM_RISK:
        risk = "Trung bình (Tổn thương tiền ung thư)"
    else:
        risk = "Thấp (Tổn thương lành tính)"

    return jsonify({
        "label": label,
        "confidence": round(prob, 4),
        "risk": risk
    })

if __name__ == "__main__":
    app.run(debug=True)
