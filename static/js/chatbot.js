// === Chatbot script (Updated for Tailwind UI) ===

// 1. Khai báo các biến DOM
const chatbotPanel = document.getElementById("chatbotPanel");
const chatbotToggle = document.getElementById("chatbotToggle");
const chatbotClose = document.getElementById("chatbotClose");
const chatbotBody = document.getElementById("chatbotBody");
const chatbotInput = document.getElementById("chatbotInput");
const chatbotSend = document.getElementById("chatbotSend");

// 2. Logic Mở/Đóng cửa sổ chat (Sửa lỗi không hiện)
chatbotToggle.onclick = () => {
    // Hiện panel
    chatbotPanel.classList.remove("hidden");
    chatbotPanel.style.display = "flex"; // Ép buộc hiển thị đè lên CSS cũ nếu có
    // Ẩn nút tròn
    chatbotToggle.classList.add("hidden");
    // Cuộn xuống cuối tin nhắn
    chatbotBody.scrollTop = chatbotBody.scrollHeight;
};

chatbotClose.onclick = () => {
    // Ẩn panel
    chatbotPanel.classList.add("hidden");
    chatbotPanel.style.display = "none"; 
    // Hiện lại nút tròn
    chatbotToggle.classList.remove("hidden");
};

// 3. Hàm thêm tin nhắn vào giao diện (Dùng Tailwind Classes)
// Hàm thêm tin nhắn vào giao diện (Đã nâng cấp để đọc Markdown)
function chatbotAppend(text, sender) {
    const row = document.createElement("div");
    
    // Căn trái (bot) hoặc phải (user)
    if (sender === "user") {
        row.className = "flex justify-end";
    } else {
        row.className = "flex justify-start";
    }

    const bubble = document.createElement("div");
    
    if (sender === "user") {
        // Tin nhắn User: Giữ nguyên textContent để an toàn
        bubble.className = "bg-medical-btn text-white rounded-lg py-2 px-3 text-sm shadow-sm max-w-[85%]";
        bubble.textContent = text;
    } else {
        // Tin nhắn Bot: Chuyển Markdown thành HTML
        bubble.className = "bg-white border border-gray-200 text-gray-700 rounded-lg py-2 px-3 text-sm shadow-sm max-w-[85%] prose prose-sm max-w-none";
        // marked.parse sẽ biến **text** thành <b>text</b>, - item thành <li>item</li>
        bubble.innerHTML = marked.parse(text);
    }

    row.appendChild(bubble);
    chatbotBody.appendChild(row);
    chatbotBody.scrollTop = chatbotBody.scrollHeight;
}

// 4. Hàm xử lý gửi tin nhắn
async function chatbotSendMessage() {
    const text = chatbotInput.value.trim();
    if (!text) return;

    // Hiển thị tin nhắn người dùng
    chatbotAppend(text, "user");
    chatbotInput.value = "";

    // Hiển thị trạng thái đang xử lý của Bot
    chatbotAppend("Đang xử lý...", "bot");
    
    // Lấy tham chiếu đến bong bóng tin nhắn vừa tạo (tin nhắn cuối cùng trong body)
    // row cuối cùng -> bubble bên trong
    const loadingBubble = chatbotBody.lastChild.firstChild;

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({message: text})
        });

        const data = await response.json();
        
        
        // Parse Markdown thành HTML và dùng innerHTML
        loadingBubble.innerHTML = marked.parse(data.reply || "Không có phản hồi từ máy chủ.");
    } catch (err) {
        console.error("Chatbot Error:", err);
        loadingBubble.textContent = "Lỗi khi gửi tin nhắn.";
        // Đổi màu bong bóng thành màu đỏ nhạt để báo lỗi (tuỳ chọn)
        loadingBubble.className = "bg-red-50 border border-red-200 text-red-700 rounded-lg py-2 px-3 text-sm shadow-sm max-w-[85%]";
    }
    
    // Cuộn xuống lần nữa sau khi load xong
    chatbotBody.scrollTop = chatbotBody.scrollHeight;
}

// 5. Gắn sự kiện click và phím Enter
if (chatbotSend) {
    chatbotSend.onclick = chatbotSendMessage;
}

if (chatbotInput) {
    chatbotInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter") chatbotSendMessage();
    });
}

// 6. Tin nhắn chào mặc định (Chỉ thêm nếu chưa có tin nhắn nào)
if (chatbotBody.children.length <= 1) { // <= 1 vì có thể có 1 tin nhắn mẫu trong HTML
    // Xóa tin nhắn mẫu trong HTML đi để tránh trùng lặp nếu cần
    chatbotBody.innerHTML = ''; 
    chatbotAppend("Xin chào 👋! Bạn có thể hỏi về các vấn đề da liễu.", "bot");
}