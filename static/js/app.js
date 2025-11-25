// ======================================================
// 1) PREVIEW ẢNH
// ======================================================
const fileInput = document.getElementById("fileInput");
const preview = document.getElementById("preview");
const uploadForm = document.getElementById("uploadForm");
const btnPredict = document.getElementById("btnPredict");

function setPreviewFromFile(file) {
    if (!file) return;
    const url = URL.createObjectURL(file);
    preview.innerHTML = `<img src="${url}" class="img-fluid rounded shadow-sm"/>`;
}

fileInput?.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (file) setPreviewFromFile(file);
});

// ======================================================
// 2) KHU VỰC KẾT QUẢ BÊN PHẢI
// ======================================================
const resultEmpty = document.getElementById("resultEmpty");
const resultContent = document.getElementById("resultContent");

const resDiagnosis = document.getElementById("res-diagnosis");
const resLabel = document.getElementById("res-label");
const resConfidence = document.getElementById("res-confidence");
const resDescription = document.getElementById("res-description");
const resRiskBadges = document.getElementById("res-risk-badges");
const resRecommendations = document.getElementById("res-recommendations");

// Badge mức nguy cơ
function renderRiskBadge(riskText) {
    let color = "secondary";

    if (riskText.includes("Cao")) color = "danger";
    else if (riskText.includes("Trung")) color = "warning";
    else if (riskText.includes("Thấp")) color = "success";

    return `<span class="badge bg-${color} fs-6 px-3 py-2">${riskText}</span>`;
}

// ======================================================
// 3) SUBMIT ẢNH → GỌI API /predict
// ======================================================
uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const file = fileInput.files[0];
    if (!file) return alert("Vui lòng chọn ảnh trước!");

    btnPredict.disabled = true;
    btnPredict.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Đang phân tích...`;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/predict", {
            method: "POST",
            body: formData
        });

        if (!res.ok) throw new Error("Lỗi máy chủ");

        const data = await res.json();
        console.log("Kết quả AI:", data);

        // Dữ liệu backend trả về: label / confidence / risk
        const label = data.label || "Không xác định";
        const confidence = typeof data.confidence === "number"
            ? (data.confidence * 100).toFixed(2)
            : "--";
        const risk = data.risk || "Không rõ";

        // Hiển thị UI
        resultEmpty.classList.add("d-none");
        resultContent.classList.remove("d-none");

        resDiagnosis.textContent = label.toUpperCase();
        resLabel.textContent = "Phân loại: " + label;
        resConfidence.textContent = "Độ tin cậy: " + confidence + "%";

        resDescription.innerHTML = `
            Đây là kết quả phân tích từ mô hình AI (ISIC).  
            Vui lòng xem thêm khuyến nghị phía dưới.
        `;

        resRiskBadges.innerHTML = renderRiskBadge(risk);

        // Gợi ý xử lý theo mức độ
        let recs = [];
        if (risk.includes("Cao")) {
            recs = [
                "Liên hệ bác sĩ da liễu càng sớm càng tốt.",
                "Không tự ý điều trị tại nhà.",
                "Theo dõi thay đổi bất thường trong 24–48 giờ."
            ];
        } else if (risk.includes("Trung")) {
            recs = [
                "Theo dõi trong 1–2 tuần.",
                "Tránh tiếp xúc nắng gắt.",
                "Nếu tổn thương lan rộng, hãy đi khám."
            ];
        } else {
            recs = [
                "Tổn thương có khả năng lành tính.",
                "Theo dõi thay đổi hình dạng & màu sắc.",
                "Chụp lại ảnh sau 2–4 tuần để so sánh."
            ];
        }

        resRecommendations.innerHTML = recs.map(r => `<li>${r}</li>`).join("");

    } catch (err) {
        console.error(err);
        alert("Không thể phân tích ảnh. Vui lòng thử lại.");
    }

    btnPredict.disabled = false;
    btnPredict.innerHTML = `<i class="bi bi-search"></i> Phân tích ảnh`;
});

// ======================================================
// 4) LỊCH SỬ THEO DÕI (Không sửa phần này)
// ======================================================
// ... (giữ nguyên phần lịch sử của bạn)

// ======================================================
// 5) CHATBOT – giữ nguyên (không liên quan lỗi UI)
// ======================================================
// ... (giữ nguyên phần chatbot của bạn)

