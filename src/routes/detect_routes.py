# routes/detect_routes.py
import os
import io
import uuid
import base64
import tempfile
import requests
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file, current_app, session
from routes.auth_routes import login_required
from PIL import Image
import numpy as np
import cv2
import matplotlib.pyplot as plt
from skimage import measure
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

from services.storage_supabase import upload_image_to_supabase
from services.firestore_patient import save_visit_firestore, get_visits_firestore

# load model
MODEL_PATH = os.environ.get("MEL_MODEL_PATH", "models/mel_nonmel_b3_finetuned.keras")
try:
    from tensorflow.keras.models import load_model
    MODEL = load_model(MODEL_PATH)
    print("[detect] loaded model:", MODEL_PATH)
except Exception as e:
    MODEL = None
    print("[detect] cannot load model:", e)

LABEL_MAP = {0: "non_mel", 1: "mel"}

TMP_DIR = os.path.join(os.getcwd(), "tmp")
os.makedirs(TMP_DIR, exist_ok=True)

# ---------------- Analyzer & detector (kept from notebook) ----------------
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
        return (lesion_pixels / total_pixels) * 100 if total_pixels > 0 else 0.0

    def calculate_metrics(self, image, mask):
        return {
            'lesion_area': self.calculate_lesion_area(mask),
            'redness_index': self.calculate_redness_index(image, mask),
            'pigmentation': self.calculate_pigmentation(image, mask),
            'patch_characteristics': self.analyze_patch_characteristics(image, mask)
        }

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

class PatientVisitSystem:
    def __init__(self):
        self.skin_detector = SimpleSkinDetector()
        self.analyzer = EnhancedLesionAnalyzer()

    def preprocess_image(self, img: Image.Image):
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img = img.resize((224, 224))
        arr = np.array(img)
        arr = np.expand_dims(arr, axis=0)
        return arr

    def predict(self, img_array):
        if MODEL is None:
            raise RuntimeError("Model not loaded")
        prob = float(MODEL.predict(img_array)[0][0])  # sigmoid
        predicted_class = 1 if prob > 0.5 else 0
        confidence = float(prob if predicted_class == 1 else 1 - prob)
        return predicted_class, confidence, [1-prob, prob]

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
        visits = get_visits_firestore(patient_id)
        if len(visits) < 2:
            return {"error":"Need at least 2 visits"}

        baseline = visits[0]
        followup = visits[-1]

        # download images to tmp files and cleanup immediately after compare
        tmp_a = None
        tmp_b = None
        try:
            r = requests.get(baseline["image_url"], timeout=10)
            if r.status_code != 200:
                return {"error":"Cannot download baseline image"}
            tmp_a = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp_a.write(r.content); tmp_a.flush(); tmp_a.close()
            a_path = tmp_a.name

            r2 = requests.get(followup["image_url"], timeout=10)
            if r2.status_code != 200:
                # cleanup a then return
                try: os.remove(a_path)
                except: pass
                return {"error":"Cannot download followup image"}
            tmp_b = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp_b.write(r2.content); tmp_b.flush(); tmp_b.close()
            b_path = tmp_b.name

            baseline_local = {"image_path": a_path, **baseline}
            followup_local = {"image_path": b_path, **followup}

            comparison = self.compare_visits_enhanced(baseline_local, followup_local)

            summary = {
                "patient_id": patient_id,
                "generated_date": datetime.utcnow().isoformat(),
                "total_visits": len(visits),
                "clinician_notes": clinician_notes,
                "metrics": {
                    "days_tracked": comparison["days_between"],
                    "area_change": comparison["changes"]["lesion_area_change"],
                    "color_change": {
                        "red": comparison["changes"]["redness_index_change"],
                        "green": comparison["changes"]["pigmentation_change"],
                        "blue": comparison["changes"]["patch_count_change"]
                    }
                },
                "visualizations": {
                    "before_after": comparison["comparison_image"],
                    "heatmap": comparison["heatmap"]
                }
            }
            return summary

        finally:
            # cleanup temp files immediately
            try:
                if tmp_a:
                    os.remove(tmp_a.name)
            except Exception:
                pass
            try:
                if tmp_b:
                    os.remove(tmp_b.name)
            except Exception:
                pass

    def generate_patient_report_pdf(self, summary):
        patient_id = summary["patient_id"]
        shared_dir = os.path.join(current_app.root_path, "shared_reports")
        os.makedirs(shared_dir, exist_ok=True)
        pdf_path = os.path.join(shared_dir, f"{patient_id}_summary.pdf")
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph(f"Patient Progress Summary – {patient_id}", styles["Title"]))
        story.append(Spacer(1, 0.2 * 72))
        if summary["clinician_notes"]:
            story.append(Paragraph("<b>Clinician Notes:</b>", styles["Heading2"]))
            story.append(Paragraph(summary["clinician_notes"], styles["Normal"]))
            story.append(Spacer(1, 0.2 * 72))
        m = summary["metrics"]
        story.append(Paragraph("<b>Progress Metrics</b>", styles["Heading2"]))
        story.append(Paragraph(f"Days tracked: {m['days_tracked']}", styles["Normal"]))
        story.append(Paragraph(f"Lesion Area Change: {m['area_change']:.2f}%", styles["Normal"]))
        story.append(Spacer(1, 0.2 * 72))
        temp_img = os.path.join(TMP_DIR, f"heatmap_{uuid.uuid4().hex}.png")
        plt.imsave(temp_img, summary["visualizations"]["heatmap"])
        story.append(Paragraph("<b>Change Heatmap</b>", styles["Heading3"]))
        story.append(RLImage(temp_img, width=400, height=400))
        story.append(Spacer(1, 0.2 * 72))
        doc.build(story)
        try:
            os.remove(temp_img)
        except:
            pass
        return pdf_path

# instantiate
system = PatientVisitSystem()

detect_bp = Blueprint("detect", __name__)

@detect_bp.route("/detect")
@login_required
def detect_ui():
    return render_template("detect.html")
@detect_bp.route("/detect/predict", methods=["POST"])
@login_required
def detect_predict():
    print("=== /detect/predict called ===")
    try:
        if MODEL is None:
            return jsonify({"error":"Model not loaded"}), 500
            
        file = request.files.get("image")
        if file is None:
            return jsonify({"error":"Image required"}), 400
            
        # --- SỬA ĐOẠN NÀY ---
        # Ưu tiên lấy từ Form, nếu không có thì lấy từ Session (người dùng đang login)
        pid = request.form.get("patient_id")
        if not pid:
            pid = session.get("uid")
            
        if not pid:
            return jsonify({"error": "Không xác định được Patient ID. Vui lòng đăng nhập lại."}), 400
        # --------------------

        visit_type = request.form.get("visit_type", "initial")
        
        # ... (Phần xử lý ảnh giữ nguyên) ...
        try:
            pil_img = Image.open(file.stream).convert("RGB")
        except Exception as e:
            print("Cannot open image:", e)
            return jsonify({"error":"Cannot open image"}), 400

        contains, mask = system.skin_detector.contains_skin(pil_img)
        if not contains:
            return jsonify({"error":"Ảnh không chứa vùng da đủ lớn hoặc rõ nét"}), 400
            
        arr = system.preprocess_image(pil_img)
        cls, conf, probs = system.predict(arr)
        prediction_data = {"class_name": LABEL_MAP[cls], "confidence": conf, "all_probabilities": probs}
        
        # convert PIL -> bytes 
        buf = io.BytesIO(); pil_img.save(buf, format="JPEG", quality=90); buf.seek(0)
        image_bytes = buf.read()
        
        # Upload
        visit_id, image_url = upload_image_to_supabase(pid, image_bytes)
        saved = save_visit_firestore(pid, visit_id, prediction_data, visit_type, image_url)
        
        return jsonify({
            "patient_id": pid,
            "visit_id": visit_id,
            "prediction": prediction_data,
            "image_url": image_url,
            "saved_meta": saved
        })
        
    except Exception as e:
        import traceback; traceback.print_exc(); print("Error:", e)
        # Trả về lỗi chi tiết để dễ debug
        return jsonify({"error": str(e)}), 500
    
@detect_bp.route("/detect/visits", methods=["GET"])
@login_required
def detect_visits():
    pid = request.args.get("patient_id","").strip() or session.get("uid")
    if not pid: return jsonify({"error":"patient_id required"}), 400
    try:
        visits = get_visits_firestore(pid)
    except Exception as e:
        import traceback; traceback.print_exc(); return jsonify({"error":"Failed to fetch visits","detail":str(e)}), 500
    return jsonify({"visits":visits})

@detect_bp.route("/detect/compare", methods=["GET"])
@login_required
def detect_compare():
    pid = request.args.get("patient_id","").strip() or session.get("uid")
    if not pid: return jsonify({"error":"patient_id required"}), 400
    
    try:
        visits = get_visits_firestore(pid)
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error":"Failed to fetch visits","detail":str(e)}), 500
        
    if len(visits) < 2: 
        return jsonify({"error":"Need at least 2 visits"}), 400
        
    baseline = visits[0]
    followup = visits[-1]
    tmp_a = None
    tmp_b = None
    
    try:
        # 1. Download ảnh Baseline
        r = requests.get(baseline["image_url"], timeout=10)
        if r.status_code != 200: return jsonify({"error":"Cannot download baseline image"}), 400
        tmp_a = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmp_a.write(r.content); tmp_a.flush(); tmp_a.close()
        a_path = tmp_a.name

        # 2. Download ảnh Followup
        r2 = requests.get(followup["image_url"], timeout=10)
        if r2.status_code != 200:
            try: os.remove(a_path)
            except: pass
            return jsonify({"error":"Cannot download followup image"}), 400
        tmp_b = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmp_b.write(r2.content); tmp_b.flush(); tmp_b.close()
        b_path = tmp_b.name

        # 3. Chạy so sánh
        baseline_local = {"image_path": a_path, **baseline}
        followup_local = {"image_path": b_path, **followup}
        progress = system.compare_visits_enhanced(baseline_local, followup_local)

        # --- ĐÂY LÀ HÀM ĐÃ SỬA LỖI ---
        def arr_to_b64(arr):
            # arr có thể là float (0-1) hoặc uint8 (0-255)
            # Nếu là float (như heatmap), cần nhân 255 và chuyển sang uint8
            if arr.dtype != np.uint8:
                # Kiểm tra xem có phải ảnh float 0-1 không
                if arr.max() <= 1.0:
                    arr = (arr * 255).astype(np.uint8)
                else:
                    arr = arr.astype(np.uint8)
            
            # Dùng PIL để save vào buffer thay vì plt.imsave
            img = Image.fromarray(arr)
            buf = io.BytesIO()
            img.save(buf, format="PNG") # PIL hỗ trợ BytesIO hoàn hảo
            buf.seek(0)
            return base64.b64encode(buf.read()).decode('ascii')
        # -----------------------------

        out = {
            "before_after": arr_to_b64(progress["comparison_image"]),
            "heatmap": arr_to_b64(progress["heatmap"]),
            "baseline_metrics": progress["baseline_metrics"],
            "followup_metrics": progress["followup_metrics"],
            "changes": progress["changes"],
            "days_between": progress["days_between"]
        }
        return jsonify(out)

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error":"Comparison failed","detail":str(e)}), 500

    finally:
        # Cleanup file tạm
        try:
            if tmp_a: os.remove(tmp_a.name)
        except Exception: pass
        try:
            if tmp_b: os.remove(tmp_b.name)
        except Exception: pass

@detect_bp.route("/detect/share", methods=["POST"])
@login_required
def detect_share():
    data = request.get_json() or {}
    pid = data.get("patient_id","").strip() or session.get("uid")
    notes = data.get("notes","")
    if not pid: return jsonify({"error":"patient_id required"}), 400
    summary = system.create_patient_summary(pid, notes)
    if "error" in summary: return jsonify(summary), 400
    try:
        pdf_path = system.generate_patient_report_pdf(summary)
    except Exception as e:
        import traceback; traceback.print_exc(); return jsonify({"error":"PDF generation failed","detail":str(e)}), 500
    return send_file(pdf_path, as_attachment=True, download_name=os.path.basename(pdf_path))
