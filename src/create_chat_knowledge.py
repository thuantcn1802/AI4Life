import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. Kết nối Firebase ---
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 2. Dữ liệu tri thức mẫu cho chatbot ---
sample_knowledge = [
    {
        "question": "melanoma là gì",
        "answer": "Melanoma là dạng ung thư da nguy hiểm nhất, xuất phát từ tế bào melanocyte. Bệnh tiến triển rất nhanh và cần phát hiện sớm."
    },
    {
        "question": "triệu chứng melanoma",
        "answer": "Dấu hiệu thường gặp: nốt ruồi thay đổi kích thước, màu sắc, hình dạng; bờ không đều; có thể chảy máu hoặc loét."
    },
    {
        "question": "bcc là gì",
        "answer": "Basal Cell Carcinoma (BCC) là ung thư tế bào đáy, dạng ung thư da phổ biến nhất nhưng ít di căn."
    },
    {
        "question": "triệu chứng bcc",
        "answer": "Xuất hiện mảng sáng bóng, ngọc trai, đôi khi có mạch máu li ti; dễ loét và chảy máu."
    },
    {
        "question": "nevus là gì",
        "answer": "Nevus là nốt ruồi lành tính, thường không nguy hiểm trừ khi có thay đổi bất thường."
    }
]

# --- 3. Hàm thêm tri thức vào Firestore ---
def create_chat_knowledge():
    collection_ref = db.collection("chat_knowledge")

    for item in sample_knowledge:
        collection_ref.add({
            "question": item["question"],
            "answer": item["answer"]
        })

    print("✔ Đã tạo collection chat_knowledge và thêm dữ liệu mẫu!")

# --- 4. Chạy ---
if __name__ == "__main__":
    create_chat_knowledge()
