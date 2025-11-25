from firebase_connect import db
import re
import string

# 1) Danh sách từ khóa để nhận diện phản hồi lỗi
ERROR_KEYWORDS = [
    "xin lỗi",
    "ai gặp sự cố",
    "không hiểu",
    "error",
    "groq",
    "failed",
    "invalid",
    "exception",
    "timeout",
    "vui lòng thử lại",
]

# 2) Làm sạch text để so sánh tốt hơn
def normalize_text(text):
    text = text.lower().strip()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text)
    return text


# 3) Tìm câu hỏi tương tự bằng mức độ giống nhau
def is_similar(a, b, threshold=0.65):
    """
    So khớp mức độ tương đồng theo tỉ lệ chung ký tự giống nhau.
    Không cần thư viện fuzzywuzzy để tránh nặng.
    """
    a = normalize_text(a)
    b = normalize_text(b)

    if not a or not b:
        return False

    matches = sum(1 for x, y in zip(a, b) if x == y)
    score = matches / max(len(a), len(b))

    return score >= threshold


def search_similar_question(user_text):
    user_norm = normalize_text(user_text)
    docs = db.collection("chat_knowledge").stream()

    best_match = None
    best_score = 0

    for d in docs:
        data = d.to_dict()
        q = normalize_text(data["question"])

        # Tính mức độ tương đồng
        matches = sum(1 for x, y in zip(q, user_norm) if x == y)
        score = matches / max(len(q), len(user_norm))

        # Lưu câu có điểm cao nhất
        if score > best_score and score >= 0.55:
            best_score = score
            best_match = data["answer"]

    return best_match



# 4) Kiểm tra phản hồi AI có hợp lệ không
def is_valid_answer(answer):

    # Câu trả lời quá ngắn không hữu ích
    if len(answer.strip()) < 20:
        return False

    # Câu trả lời lỗi
    for k in ERROR_KEYWORDS:
        if k in answer.lower():
            return False

    # Câu trả lời chỉ có 1 dòng, quá ít thông tin
    if len(answer.split()) < 5:
        return False

    return True


# 5) Lưu tri thức mới vào Firestore
def save_knowledge(question, answer):
    if not is_valid_answer(answer):
        print("[Knowledge] Bỏ qua – câu trả lời AI không hợp lệ, không lưu.")
        return

    # Làm sạch text
    q_norm = normalize_text(question)
    docs = db.collection("chat_knowledge").stream()

    # Kiểm tra câu hỏi trùng -> không lưu
    for d in docs:
        data = d.to_dict()
        if is_similar(q_norm, normalize_text(data["question"])):
            print("[Knowledge] Bỏ qua – câu hỏi tương tự đã tồn tại.")
            return

    # Lưu tri thức
    db.collection("chat_knowledge").add({
        "question": question,
        "answer": answer
    })

    print("[Knowledge] Đã lưu tri thức mới vào Firestore.")
