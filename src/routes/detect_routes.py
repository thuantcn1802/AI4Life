# src/routes/detect_routes.py
import os, io, json, uuid, shutil, base64
from datetime import datetime
from flask import (
    Blueprint, render_template, request, jsonify, current_app,
    send_file
)
from routes.auth_routes import login_required
from PIL import Image
import numpy as np
import cv2
import matplotlib.pyplot as plt
from skimage import measure
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

# -------------------------
# MODEL LOAD - chỉnh path nếu cần
# -------------------------
MODEL_PATH = os.environ.get("MEL_MODEL_PATH", "models/mel_nonmel_b3_finetuned.keras")
try:
    from tensorflow.keras.models import load_model
    MODEL = load_model(MODEL_PATH)
    print("[detect] Model loaded:", MODEL_PATH)
except Exception as e:
    MODEL = None
    print("[detect] Warning: could not load model:", e)

LABEL_MAP = {0: "non_mel", 1: "mel"}

# -------------------------
# Ensure directories
# -------------------------
BASE_DATA = os.path.join(os.getcwd(), "patient_data")
SHARED = os.path.join(os.getcwd(), "shared_reports")
os.makedirs(BASE_DATA, exist_ok=True)
os.makedirs(SHARED, exist_ok=True)


# -------------------------
# EnhancedLesionAnalyzer (GIỮ NGUYÊN)
# -------------------------
class EnhancedLesionAnalyzer:
    def calculate_redness_index(self, image, mask):
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        a_channel = lab[:, :, 1]
        lesion_a = a_channel[mask > 0]
        if len(lesion_a) == 0:
            return 0.0
        return float(np.mean(lesion_a))

    def calculate_pigmentation(self, image, mask):
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        b_channel = lab[:, :, 2]
        lesion_b = b_channel[mask > 0]
        if len(lesion_b) == 0:
            return 0.0
        return float(np.mean(lesion_b))

    def analyze_patch_characteristics(self, image, mask):
        labeled_mask = measure.label(mask)
        regions = measure.regionprops(labeled_mask)
        if not regions:
            return {
                'patch_count': 0,
                'mean_size': 0,
                'size_distribution': [],
                'circularity_mean': 0,
                'irregularity_index': 0
            }
        patch_areas = [region.area for region in regions]
        patch_perimeters = [region.perimeter for region in regions]
        circularities = []
        for area, perimeter in zip(patch_areas, patch_perimeters):
            if perimeter > 0:
                circularity = 4*np.pi * area / (perimeter**2)
                circularities.append(circularity)
        irregularity_index = 1 - np.mean(circularities) if circularities else 0
        return {
            'patch_count': len(regions),
            'mean_size': float(np.mean(patch_areas)),
            'size_distribution': patch_areas,
            'circularity_mean': float(np.mean(circularities)) if circularities else 0,
            'irregularity_index': float(irregularity_index)
        }

    def calculate_lesion_area(self, mask):
        total_pixels = mask.shape[0] * mask.shape[1]
        lesion_pixels = int(np.sum(mask > 0))
        return (lesion_pixels / total_pixels) * 100 if total_pixels>0 else 0.0

    def calculate_metrics(self, image, mask):
        return {
            'lesion_area': self.calculate_lesion_area(mask),
            'redness_index': self.calculate_redness_index(image, mask),
            'pigmentation': self.calculate_pigmentation(image, mask),
            'patch_characteristics': self.analyze_patch_characteristics(image, mask)
        }


# -------------------------
# SimpleSkinDetector (GIỮ NGUYÊN)
# -------------------------
class SimpleSkinDetector:
    def __init__(self):
        self.skin_ranges = [
            (np.array([0,20,70]), np.array([20,255,255])),
            (np.array([3,30,60]), np.array([25,255,255])),
            (np.array([5,40,50]), np.array([30,255,255]))
        ]
        self.ycrcb_ranges = [
            (np.array([0,133,77]), np.array([255,173,127])),
            (np.array([0,120,70]), np.array([255,160,120])),
            (np.array([0,110,60]), np.array([255,150,110]))
        ]

    def contains_skin(self, image):
        img_array = np.array(image)
        if img_array.size == 0:
            return False, np.zeros((1,1), dtype=np.uint8)
        hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV)
        ycrcb = cv2.cvtColor(img_array, cv2.COLOR_RGB2YCrCb)
        skin_mask = np.zeros(img_array.shape[:2], dtype=np.uint8)
        for lower, upper in self.skin_ranges:
            mask = cv2.inRange(hsv, lower, upper)
            skin_mask = cv2.bitwise_or(skin_mask, mask)
        for lower, upper in self.ycrcb_ranges:
            mask = cv2.inRange(ycrcb, lower, upper)
            skin_mask = cv2.bitwise_or(skin_mask, mask)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11,11))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
        skin_percentage = np.sum(skin_mask>0)/(skin_mask.size)*100
        return (skin_percentage > 2), skin_mask


# -------------------------
# PatientVisitSystem (GIỮ NGUYÊN)
# -------------------------
class PatientVisitSystem:
    def __init__(self):
        self.current_patient_id = None
        self.current_visit_data = None
        self.skin_detector = SimpleSkinDetector()
        self.analyzer = EnhancedLesionAnalyzer()

    def preprocess_image(self, img):
        # img: PIL.Image
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img = img.resize((224, 224))
        arr = np.array(img)
        arr = np.expand_dims(arr, axis=0)
        return arr

    def predict(self, img_array):
        if MODEL is None:
            raise RuntimeError("Model not loaded")
        prob = float(MODEL.predict(img_array)[0][0])  # sigmoid output
        predicted_class = 1 if prob > 0.5 else 0
        confidence = float(prob if predicted_class == 1 else 1 - prob)
        return predicted_class, confidence, [1-prob, prob]

    def save_patient_visit(self, patient_id, image, prediction_data, visit_type="initial"):
        patient_dir = os.path.join(BASE_DATA, patient_id)
        os.makedirs(patient_dir, exist_ok=True)

        visit_id = str(uuid.uuid4())
        visit_dir = os.path.join(patient_dir, visit_id)
        os.makedirs(visit_dir, exist_ok=True)

        if image.mode == 'RGBA':
            image = image.convert('RGB')
        image_path = os.path.join(visit_dir, 'image.jpg')
        image.save(image_path, format='JPEG', quality=90)

        prediction_path = os.path.join(visit_dir, 'prediction.json')
        with open(prediction_path, 'w') as f:
            json.dump({
                'visit_id': visit_id,
                'patient_id': patient_id,
                'visit_type': visit_type,
                'timestamp': datetime.now().isoformat(),
                'prediction': prediction_data['class_name'],
                'confidence': float(prediction_data['confidence']),
                'all_probabilities': [float(p) for p in prediction_data['all_probabilities']]
            }, f, ensure_ascii=False)

        return visit_id

    def get_patient_visits(self, patient_id):
        visits=[]
        patient_dir = os.path.join(BASE_DATA, patient_id)
        if not os.path.exists(patient_dir):
            return visits
        for visit_dir in os.listdir(patient_dir):
            folder = os.path.join(patient_dir, visit_dir)
            if os.path.isdir(folder):
                json_path = os.path.join(folder, 'prediction.json')
                if os.path.exists(json_path):
                    with open(json_path, 'r') as f:
                        data = json.load(f)
                        data['image_path'] = os.path.join(folder, 'image.jpg')
                        visits.append(data)
        visits.sort(key=lambda x: x['timestamp'])
        return visits

    def compare_visits_enhanced(self, baseline, followup):
        baseline_img = Image.open(baseline['image_path'])
        followup_img = Image.open(followup['image_path'])

        if baseline_img.mode == 'RGBA': baseline_img = baseline_img.convert('RGB')
        if followup_img.mode == 'RGBA': followup_img = followup_img.convert('RGB')

        size=(300,300)
        baseline_img = baseline_img.resize(size)
        followup_img = followup_img.resize(size)

        baseline_arr=np.array(baseline_img)
        followup_arr=np.array(followup_img)

        baseline_gray=cv2.cvtColor(baseline_arr,cv2.COLOR_RGB2GRAY)
        followup_gray=cv2.cvtColor(followup_arr,cv2.COLOR_RGB2GRAY)

        _,baseline_mask=cv2.threshold(baseline_gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        _,followup_mask=cv2.threshold(followup_gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)

        baseline_metrics=self.analyzer.calculate_metrics(baseline_arr,baseline_mask)
        followup_metrics=self.analyzer.calculate_metrics(followup_arr,followup_mask)

        changes={
            'lesion_area_change': ((followup_metrics['lesion_area']-baseline_metrics['lesion_area'])/baseline_metrics['lesion_area']*100) if baseline_metrics['lesion_area']>0 else 0,
            'redness_index_change': ((followup_metrics['redness_index']-baseline_metrics['redness_index'])/baseline_metrics['redness_index']*100) if baseline_metrics['redness_index']>0 else 0,
            'pigmentation_change': ((followup_metrics['pigmentation']-baseline_metrics['pigmentation'])/baseline_metrics['pigmentation']*100) if baseline_metrics['pigmentation']>0 else 0,
            'patch_count_change': followup_metrics['patch_characteristics']['patch_count']-baseline_metrics['patch_characteristics']['patch_count'],
            'irregularity_change': followup_metrics['patch_characteristics']['irregularity_index']-baseline_metrics['patch_characteristics']['irregularity_index']
        }

        comparison=np.hstack((baseline_arr,followup_arr))

        diff=np.abs(baseline_gray.astype(float)-followup_gray.astype(float))
        if diff.max()>0: diff=diff/diff.max()

        heatmap=np.zeros((*diff.shape,3))
        heatmap[diff<0.3]=[0,1,0]
        heatmap[(diff>=0.3)&(diff<0.7)]=[1,1,0]
        heatmap[diff>=0.7]=[1,0,0]

        days=(datetime.fromisoformat(followup['timestamp'])-datetime.fromisoformat(baseline['timestamp'])).days

        return {
            'comparison_image':comparison,
            'heatmap':heatmap,
            'baseline_metrics':baseline_metrics,
            'followup_metrics':followup_metrics,
            'changes':changes,
            'baseline_image':baseline_arr,
            'followup_image':followup_arr,
            'baseline_mask':baseline_mask,
            'followup_mask':followup_mask,
            'baseline_prediction':baseline['prediction'],
            'followup_prediction':followup['prediction'],
            'baseline_confidence':baseline['confidence'],
            'followup_confidence':followup['confidence'],
            'days_between':days
        }

    def create_patient_summary(self, patient_id, clinician_notes=""):
        patient_dir = os.path.join(BASE_DATA, patient_id)
        if not os.path.exists(patient_dir):
            return {"error":"No data found for this patient"}
        visits = self.get_patient_visits(patient_id)
        if len(visits) < 2:
            return {"error":"Need at least 2 visits"}
        baseline = visits[0]
        followup = visits[-1]
        comparison = self.compare_visits_enhanced(baseline, followup)
        summary = {
            "patient_id":patient_id,
            "generated_date":datetime.now().isoformat(),
            "total_visits":len(visits),
            "clinician_notes":clinician_notes,
            "metrics":{
                "days_tracked":comparison["days_between"],
                "area_change":comparison["changes"]["lesion_area_change"],
                "color_change":{
                    "red":comparison["changes"]["redness_index_change"],
                    "green":comparison["changes"]["pigmentation_change"],
                    "blue":comparison["changes"]["patch_count_change"]
                }
            },
            "visualizations":{
                "before_after":comparison["comparison_image"],
                "heatmap":comparison["heatmap"]
            }
        }
        return summary

    def generate_patient_report_pdf(self, summary):
        patient_id=summary["patient_id"]
        pdf_path=os.path.join(SHARED,f"{patient_id}_summary.pdf")
        doc=SimpleDocTemplate(pdf_path,pagesize=letter)
        styles=getSampleStyleSheet()
        story=[]
        story.append(Paragraph(f"Patient Progress Summary – {patient_id}",styles["Title"]))
        story.append(Spacer(1,0.2*72))
        if summary["clinician_notes"]:
            story.append(Paragraph("<b>Clinician Notes:</b>",styles["Heading2"]))
            story.append(Paragraph(summary["clinician_notes"],styles["Normal"]))
            story.append(Spacer(1,0.2*72))
        m=summary["metrics"]
        story.append(Paragraph("<b>Progress Metrics</b>",styles["Heading2"]))
        story.append(Paragraph(f"Days tracked: {m['days_tracked']}",styles["Normal"]))
        story.append(Paragraph(f"Lesion Area Change: {m['area_change']:.2f}%",styles["Normal"]))
        story.append(Spacer(1,0.2*72))
        temp_img="temp_heatmap.png"
        plt.imsave(temp_img,summary["visualizations"]["heatmap"])
        story.append(Paragraph("<b>Change Heatmap</b>",styles["Heading3"]))
        story.append(RLImage(temp_img,width=400,height=400))
        story.append(Spacer(1,0.2*72))
        doc.build(story)
        os.remove(temp_img)
        return pdf_path


# -------------------------
# instantiate system
# -------------------------
system = PatientVisitSystem()

# -------------------------
# Blueprint
# -------------------------
detect_bp = Blueprint("detect", __name__)


@detect_bp.route("/detect")
@login_required
def detect_ui():
    return render_template("detect.html")


@detect_bp.route("/detect/predict", methods=["POST"])
@login_required
def detect_predict():
    """
    POST fields:
      - image (file)
      - patient_id (optional)
      - visit_type: initial|followup (optional)
    """
    if MODEL is None:
        return jsonify({"error":"Model not loaded on server"}), 500

    file = request.files.get("image")
    if file is None:
        return jsonify({"error":"Image file required"}), 400

    patient_id = request.form.get("patient_id", "").strip()
    visit_type = request.form.get("visit_type", "initial")

    if not patient_id:
        patient_id = f"patient_{uuid.uuid4().hex[:8]}"

    try:
        img = Image.open(file.stream)
    except Exception as e:
        return jsonify({"error":"Cannot open image"}), 400

    contains_skin, skin_mask = system.skin_detector.contains_skin(img)
    if not contains_skin:
        # return mask visualization as base64 optional
        return jsonify({"error":"Image does not contain enough skin tissue"}), 400

    img_arr = system.preprocess_image(img)
    cls, conf, probs = system.predict(img_arr)

    prediction_data = {
        "class_name": LABEL_MAP[cls],
        "confidence": conf,
        "all_probabilities": probs
    }

    visit_id = system.save_patient_visit(patient_id, img, prediction_data, visit_type)

    return jsonify({
        "patient_id": patient_id,
        "visit_id": visit_id,
        "prediction": prediction_data
    })


@detect_bp.route("/detect/visits", methods=["GET"])
@login_required
def detect_visits():
    pid = request.args.get("patient_id", "").strip()
    if not pid:
        return jsonify({"error":"patient_id required"}), 400
    visits = system.get_patient_visits(pid)
    # convert paths to URLs
    for v in visits:
        v["image_url"] = "/"+v["image_path"].replace("\\", "/")
    return jsonify({"visits": visits})


@detect_bp.route("/detect/compare", methods=["GET"])
@login_required
def detect_compare():
    """
    Query params:
      - patient_id
    Returns JSON with base64 images: before_after (png), heatmap (png), and metrics
    """
    pid = request.args.get("patient_id", "").strip()
    if not pid:
        return jsonify({"error":"patient_id required"}), 400
    visits = system.get_patient_visits(pid)
    if len(visits) < 2:
        return jsonify({"error":"Need at least 2 visits"}), 400
    baseline = visits[0]
    followup = visits[-1]
    progress = system.compare_visits_enhanced(baseline, followup)

    # convert numpy images to png bytes
    def arr_to_base64_png(arr):
        buf = io.BytesIO()
        plt.imsave(buf, arr, format='png')
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('ascii')

    before_after_b64 = arr_to_base64_png(progress['comparison_image'])
    heatmap_b64 = arr_to_base64_png(progress['heatmap'])

    return jsonify({
        "before_after": before_after_b64,
        "heatmap": heatmap_b64,
        "baseline_metrics": progress['baseline_metrics'],
        "followup_metrics": progress['followup_metrics'],
        "changes": progress['changes'],
        "days_between": progress['days_between']
    })


@detect_bp.route("/detect/share", methods=["POST"])
@login_required
def detect_share():
    """
    Body JSON:
      - patient_id
      - notes (clinician notes)
    Returns: pdf file
    """
    data = request.get_json() or {}
    pid = data.get("patient_id","").strip()
    notes = data.get("notes","")
    if not pid:
        return jsonify({"error":"patient_id required"}), 400

    summary = system.create_patient_summary(pid, notes)
    if "error" in summary:
        return jsonify(summary), 400

    pdf_path = system.generate_patient_report_pdf(summary)
    if not os.path.exists(pdf_path):
        return jsonify({"error":"PDF generation failed"}), 500

    return send_file(pdf_path, as_attachment=True, download_name=os.path.basename(pdf_path))
