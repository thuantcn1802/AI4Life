// static/js/detect.js

document.addEventListener("DOMContentLoaded", () => {
    // --- KHAI BÁO BIẾN ---
    const fileInput = document.getElementById("fileInput");
    const uploadForm = document.getElementById("predictForm");
    const btnPredict = document.getElementById("btnPredict");
    const resultEmpty = document.getElementById("resultEmpty");
    const resultContent = document.getElementById("resultContent");
    const resSummary = document.getElementById("resSummary");
    const resConfidence = document.getElementById("resConfidence");
    const resRisk = document.getElementById("resRisk");
    const btnShare = document.getElementById("btnShare");
    const btnCompare = document.getElementById("btnCompare");
    const btnLoadVisits = document.getElementById("btnLoadVisits");
    const visitsList = document.getElementById("visitsList");

    // [QUAN TRỌNG] Biến lưu trữ kết quả so sánh tạm thời
    let currentCompareData = null;

    // --- 1. UPLOAD & PREDICT ---
    if (uploadForm) {
        uploadForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (!fileInput.files.length) {
                alert("Vui lòng chọn ảnh trước.");
                return;
            }

            // Reset dữ liệu so sánh cũ khi phân tích ảnh mới
            currentCompareData = null; 
            const compareArea = document.getElementById("compareArea");
            if(compareArea) compareArea.innerHTML = "";

            const visitType = document.querySelector('input[name="visit_type"]:checked').value;
            const formData = new FormData();
            formData.append("image", fileInput.files[0]);
            formData.append("visit_type", visitType);

            btnPredict.disabled = true;
            const originalBtnText = btnPredict.innerHTML;
            btnPredict.innerHTML = `<svg class="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> <span>Đang xử lý...</span>`;

            try {
                const res = await fetch("/detect/predict", {
                    method: "POST",
                    body: formData,
                    credentials: "include"
                });
                const data = await res.json();
                
                if (!res.ok || data.error) throw new Error(data.error || "Lỗi server");

                resultEmpty.classList.add("hidden");
                resultContent.classList.remove("hidden");
                resultContent.classList.add("flex");

                resSummary.innerText = data.prediction.class_name;
                resConfidence.innerText = (data.prediction.confidence * 100).toFixed(1) + "%";
                
                if (data.prediction.class_name === "mel") {
                    resRisk.innerHTML = '<span class="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-red-100 text-red-700 text-sm font-bold border border-red-200">⚠️ Nguy cơ cao (Melanoma)</span>';
                } else {
                    resRisk.innerHTML = '<span class="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-green-100 text-green-700 text-sm font-bold border border-green-200">✅ Lành tính / Ít nguy cơ</span>';
                }
                loadHistory();
            } catch (err) {
                alert("Lỗi: " + err.message);
            } finally {
                btnPredict.disabled = false;
                btnPredict.innerHTML = originalBtnText;
            }
        });
    }

    // --- 2. LOAD HISTORY ---
    async function loadHistory() {
        try {
            const res = await fetch("/detect/visits", { credentials: "include" });
            const data = await res.json();
            if (data.error) return;
            
            if (visitsList && data.visits) {
                if (data.visits.length === 0) {
                    visitsList.innerHTML = "<div class='col-span-full text-center py-4 text-gray-400'>Chưa có lịch sử khám bệnh.</div>";
                } else {
                    visitsList.innerHTML = data.visits.map(v => `
                        <div class="bg-gray-50 border border-gray-100 p-3 rounded-lg hover:shadow-md transition-shadow">
                            <div class="flex justify-between items-start mb-2">
                                <span class="text-xs font-bold uppercase ${v.visit_type === 'initial' ? 'text-teal-700 bg-teal-50 px-2 py-0.5 rounded' : 'text-gray-600 bg-gray-200 px-2 py-0.5 rounded'}">${v.visit_type}</span>
                                <span class="text-xs text-gray-400">${new Date(v.timestamp).toLocaleDateString()}</span>
                            </div>
                            <div class="flex items-center justify-between">
                                <span class="font-medium text-gray-700 text-sm truncate">${v.prediction}</span>
                                <span class="text-xs font-bold text-teal-600">${(v.confidence * 100).toFixed(0)}%</span>
                            </div>
                        </div>
                    `).join("");
                }
            }
        } catch (e) { console.error(e); }
    }
    loadHistory();
    if (btnLoadVisits) btnLoadVisits.addEventListener("click", loadHistory);

    // --- 3. COMPARE FUNCTION ---
    if (btnCompare) {
        btnCompare.addEventListener("click", async () => {
             const compareArea = document.getElementById("compareArea");
             compareArea.innerHTML = `<div class="bg-white rounded-xl p-8 text-center border"><div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-medical-btn"></div><p class="mt-2 text-gray-500">Đang so sánh...</p></div>`;

             try {
                 const res = await fetch("/detect/compare", { credentials: "include" });
                 const data = await res.json();
                 if (!res.ok || data.error) throw new Error(data.error || "Lỗi so sánh");
                 
                 // [QUAN TRỌNG] Lưu dữ liệu vào biến toàn cục để dùng cho in ấn
                 currentCompareData = data;

                 const areaChange = data.changes.lesion_area_change.toFixed(2);
                 const rednessChange = data.changes.redness_index_change.toFixed(2);
                 const days = data.days_between;

                 const htmlContent = `
                    <div class="bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden animate-fade-in-up">
                        <div class="bg-medical-dark p-4 text-white flex justify-between items-center">
                            <h3 class="font-bold text-lg flex items-center gap-2">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
                                Kết quả So sánh
                            </h3>
                            <span class="bg-white/20 px-3 py-1 rounded text-sm font-mono">${days} ngày</span>
                        </div>
                        <div class="p-6">
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
                                <div class="space-y-2">
                                    <p class="text-center font-semibold text-gray-700">Trực quan</p>
                                    <div class="rounded-xl overflow-hidden border border-gray-200 shadow-sm"><img src="data:image/png;base64,${data.before_after}" class="w-full h-auto object-cover"></div>
                                </div>
                                <div class="space-y-2">
                                    <p class="text-center font-semibold text-gray-700">Heatmap</p>
                                    <div class="rounded-xl overflow-hidden border border-gray-200 shadow-sm"><img src="data:image/png;base64,${data.heatmap}" class="w-full h-auto object-cover"></div>
                                </div>
                            </div>
                            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                <div class="bg-gray-50 p-4 rounded-xl border border-gray-100 text-center">
                                    <p class="text-xs text-gray-500 uppercase font-bold mb-1">Diện tích</p>
                                    <p class="text-xl font-bold ${areaChange > 0 ? 'text-red-500' : 'text-green-600'}">${areaChange > 0 ? '+' : ''}${areaChange}%</p>
                                </div>
                                <div class="bg-gray-50 p-4 rounded-xl border border-gray-100 text-center">
                                    <p class="text-xs text-gray-500 uppercase font-bold mb-1">Độ đỏ</p>
                                    <p class="text-xl font-bold ${rednessChange > 0 ? 'text-red-500' : 'text-green-600'}">${rednessChange > 0 ? '+' : ''}${rednessChange}%</p>
                                </div>
                                <div class="bg-gray-50 p-4 rounded-xl border border-gray-100 text-center">
                                    <p class="text-xs text-gray-500 uppercase font-bold mb-1">Độ không đều</p>
                                    <p class="text-xl font-bold text-gray-700">${data.changes.irregularity_change.toFixed(3)}</p>
                                </div>
                            </div>
                        </div>
                    </div>`;
                 compareArea.innerHTML = htmlContent;
                 compareArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
             } catch (e) {
                 compareArea.innerHTML = `<div class="bg-red-50 text-red-600 p-4 rounded-lg">Lỗi: ${e.message}</div>`;
             }
        });
    }

    // --- 4. EXPORT PDF (NATIVE WINDOW - CÓ KÈM SO SÁNH) ---
    if (btnShare) {
        btnShare.addEventListener("click", () => {
            const imgPreview = document.getElementById('imagePreview');
            if (!imgPreview || imgPreview.src.length < 100 || imgPreview.classList.contains('hidden')) { 
                alert("Vui lòng tải ảnh lên và phân tích trước khi xuất báo cáo.");
                return;
            }

            // Dữ liệu cơ bản
            const data = {
                date: new Date().toLocaleDateString('vi-VN'),
                id: 'SC-' + Math.floor(Math.random() * 100000),
                imgSrc: imgPreview.src,
                summary: document.getElementById('resSummary').innerText,
                riskHtml: document.getElementById('resRisk').innerHTML, 
                confidence: document.getElementById('resConfidence').innerText,
                notes: document.getElementById('clinicianNotes').value || "Không có ghi chú lâm sàng."
            };

            // Chuẩn bị HTML cho phần So sánh (Nếu có)
            let compareSectionHtml = '';
            
            if (currentCompareData) {
                const areaChange = currentCompareData.changes.lesion_area_change.toFixed(2);
                const rednessChange = currentCompareData.changes.redness_index_change.toFixed(2);
                
                compareSectionHtml = `
                    <div style="page-break-before: always;"></div> <div class="mt-8 pt-6 border-t-2 border-dashed border-gray-300">
                        <div class="flex items-center gap-2 mb-4">
                            <div class="w-1 h-6 bg-medical-dark"></div>
                            <h3 class="font-bold text-gray-600 uppercase text-sm">Phân tích So sánh (Theo dõi diễn tiến)</h3>
                            <span class="ml-auto bg-gray-100 px-3 py-1 rounded text-xs font-bold text-gray-600">Delta: ${currentCompareData.days_between} ngày</span>
                        </div>

                        <div class="grid grid-cols-2 gap-6 mb-6">
                            <div>
                                <p class="text-xs text-center font-bold text-gray-500 mb-2">Hình ảnh trực quan (Trước/Sau)</p>
                                <div class="border border-gray-200 p-1 rounded">
                                    <img src="data:image/png;base64,${currentCompareData.before_after}" class="w-full h-auto object-contain">
                                </div>
                            </div>
                            <div>
                                <p class="text-xs text-center font-bold text-gray-500 mb-2">Bản đồ nhiệt thay đổi</p>
                                <div class="border border-gray-200 p-1 rounded">
                                    <img src="data:image/png;base64,${currentCompareData.heatmap}" class="w-full h-auto object-contain">
                                </div>
                            </div>
                        </div>

                        <div class="grid grid-cols-3 gap-4">
                            <div class="bg-gray-50 p-3 rounded border border-gray-100 text-center">
                                <p class="text-[10px] text-gray-500 uppercase font-bold">Thay đổi diện tích</p>
                                <p class="text-lg font-bold ${areaChange > 0 ? 'text-red-600' : 'text-green-600'}">
                                    ${areaChange > 0 ? '+' : ''}${areaChange}%
                                </p>
                            </div>
                            <div class="bg-gray-50 p-3 rounded border border-gray-100 text-center">
                                <p class="text-[10px] text-gray-500 uppercase font-bold">Thay đổi độ đỏ</p>
                                <p class="text-lg font-bold ${rednessChange > 0 ? 'text-red-600' : 'text-green-600'}">
                                    ${rednessChange > 0 ? '+' : ''}${rednessChange}%
                                </p>
                            </div>
                            <div class="bg-gray-50 p-3 rounded border border-gray-100 text-center">
                                <p class="text-[10px] text-gray-500 uppercase font-bold">Độ không đều</p>
                                <p class="text-lg font-bold text-gray-700">
                                    ${currentCompareData.changes.irregularity_change.toFixed(3)}
                                </p>
                            </div>
                        </div>
                    </div>
                `;
            }

            // HTML Nội dung In
            const printContent = `
                <!DOCTYPE html>
                <html lang="vi">
                <head>
                    <meta charset="UTF-8">
                    <title>Báo cáo Chẩn đoán - ${data.id}</title>
                    <script src="https://cdn.tailwindcss.com"></script>
                    <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;600;700&display=swap" rel="stylesheet">
                    <style>
                        body { font-family: 'Be Vietnam Pro', sans-serif; -webkit-print-color-adjust: exact; }
                        @page { size: A4; margin: 0; }
                        .no-break { page-break-inside: avoid; }
                    </style>
                    <script>
                        tailwind.config = {
                            theme: {
                                extend: { colors: { 'medical-teal': '#8CDAD4', 'medical-dark': '#2D8B84' } }
                            }
                        }
                    </script>
                </head>
                <body class="bg-white p-10 max-w-[210mm] mx-auto min-h-screen relative">
                    
                    <div class="flex justify-between items-end border-b-2 border-medical-dark pb-6 mb-8">
                        <div>
                            <h1 class="text-3xl font-bold text-teal-700 uppercase tracking-wide">Phiếu Kết Quả</h1>
                            <p class="text-gray-500 mt-2 font-medium">Hệ thống hỗ trợ chẩn đoán SkinCare AI</p>
                        </div>
                        <div class="text-right">
                            <p class="text-sm font-bold text-gray-700">Ngày: <span class="font-normal">${data.date}</span></p>
                            <p class="text-sm font-bold text-gray-700">Mã hồ sơ: <span class="font-normal">${data.id}</span></p>
                        </div>
                    </div>

                    <div class="grid grid-cols-2 gap-10 mb-6 no-break">
                        <div>
                            <div class="flex items-center gap-2 mb-3">
                                <div class="w-1 h-6 bg-teal-500"></div>
                                <h3 class="font-bold text-gray-600 uppercase text-sm">Hình ảnh tổn thương</h3>
                            </div>
                            <div class="border border-gray-200 rounded-lg p-2 bg-gray-50 flex items-center justify-center h-[300px]">
                                <img src="${data.imgSrc}" class="max-w-full max-h-full object-contain rounded">
                            </div>
                        </div>

                        <div>
                            <div class="flex items-center gap-2 mb-3">
                                <div class="w-1 h-6 bg-teal-500"></div>
                                <h3 class="font-bold text-gray-600 uppercase text-sm">Kết quả phân tích</h3>
                            </div>

                            <div class="bg-teal-50/50 rounded-xl border border-teal-100 p-6 mb-6">
                                <div class="mb-4">
                                    <p class="text-xs text-gray-500 uppercase font-semibold mb-1">Kết luận:</p>
                                    <p class="text-2xl font-bold text-gray-800">${data.summary}</p>
                                </div>
                                <div class="mb-4">
                                    <p class="text-xs text-gray-500 uppercase font-semibold mb-1">Đánh giá nguy cơ:</p>
                                    <div class="text-lg">${data.riskHtml}</div>
                                </div>
                                <div>
                                    <div class="flex justify-between items-end mb-1">
                                        <span class="text-xs text-gray-500 uppercase font-semibold">Độ tin cậy</span>
                                        <span class="text-xl font-bold text-teal-700">${data.confidence}</span>
                                    </div>
                                    <div class="w-full bg-gray-200 rounded-full h-2">
                                        <div class="bg-teal-600 h-2 rounded-full" style="width: ${data.confidence}"></div>
                                    </div>
                                </div>
                            </div>

                            <div class="border border-gray-200 rounded-xl p-5 shadow-sm">
                                <p class="text-sm font-bold text-gray-700 mb-2 border-b border-gray-100 pb-2">Ghi chú bác sĩ:</p>
                                <p class="text-sm text-gray-600 italic leading-relaxed whitespace-pre-wrap">${data.notes}</p>
                            </div>
                        </div>
                    </div>

                    ${compareSectionHtml}

                    <div class="mt-12 pt-6 border-t border-gray-200 text-center no-break">
                        <p class="text-xs text-gray-400 italic mb-2">
                            * Lưu ý: Kết quả này được tạo bởi AI và chỉ mang tính chất tham khảo sàng lọc. 
                            Vui lòng tham vấn bác sĩ chuyên khoa để có chẩn đoán chính xác nhất.
                        </p>
                        <p class="text-xs text-gray-300 font-semibold">Powered by AI Detection Project © 2025</p>
                    </div>

                    <script>
                        window.onload = function() {
                            setTimeout(function() { window.print(); }, 800);
                        }
                    <\/script>
                </body>
                </html>
            `;

            const printWindow = window.open('', '_blank');
            printWindow.document.open();
            printWindow.document.write(printContent);
            printWindow.document.close();
        });
    }
});