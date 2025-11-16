from firebase_connect import get_disease

NAME_TO_CODE = {
    "melanoma": "MEL",
    "actinic keratosis": "AKIEC",
    "pigmented benign keratosis": "BKL",
    "seborrheic keratosis": "BKL",
    "vascular lesion": "VASC",
    "basal cell carcinoma": "BCC",
    "squamous cell carcinoma": "SCC",
    "dermatofibroma": "DF",
    "nevus": "NV"
}

def detect_disease_in_text(text):
    text = text.lower()
    for name, code in NAME_TO_CODE.items():
        if name in text:
            return code
    return None


def generate_reply(text):
    text = text.lower()

    code = detect_disease_in_text(text)

    # Nếu user đang hỏi về bệnh cụ thể
    if code:
        disease = get_disease(code)
        if disease is None:
            return "Xin lỗi, tôi không tìm thấy thông tin bệnh trong hệ thống."

        reply = (
            f"{disease['name']}\n\n"
            f"Mô tả:\n{disease['description']}\n\n"
            f"Dấu hiệu:\n- " + "\n- ".join(disease["signs"]) + "\n\n"
            f"Mức độ nguy hiểm:\n{disease['danger_level']}\n\n"
            f"Phòng tránh:\n- " + "\n- ".join(disease["prevention"]) + "\n\n"
            f"Điều trị:\n- " + "\n- ".join(disease["treatment"]) + "\n\n"
            f"Khuyến nghị:\n{disease['recommended_action']}"
        )

        return reply

    # Nếu user chào hỏi
    if "chào" in text or "hello" in text:
        return "Xin chào! Tôi là AI4Life. Bạn muốn hỏi về loại bệnh da nào?"

    # Nếu hỏi triệu chứng nhưng không nói tên bệnh
    if "triệu chứng" in text:
        return "Bạn muốn hỏi triệu chứng của bệnh nào? (Ví dụ: melanoma, BCC, nevus...)"

    return "Tôi đã nhận được câu hỏi của bạn. Bạn muốn hỏi về bệnh gì?"
