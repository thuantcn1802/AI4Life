// === Chatbot script ===
const chatbotPanel = document.getElementById("chatbotPanel");
const chatbotToggle = document.getElementById("chatbotToggle");
const chatbotClose = document.getElementById("chatbotClose");
const chatbotBody = document.getElementById("chatbotBody");
const chatbotInput = document.getElementById("chatbotInput");
const chatbotSend = document.getElementById("chatbotSend");

chatbotToggle.onclick = () => chatbotPanel.classList.add("open");
chatbotClose.onclick = () => chatbotPanel.classList.remove("open");

function chatbotAppend(text, sender) {
    const box = document.createElement("div");
    box.className = "chatbot-msg-box";

    const msg = document.createElement("div");
    msg.className = "chatbot-msg " + sender;
    msg.textContent = text;

    box.appendChild(msg);
    chatbotBody.appendChild(box);
    chatbotBody.scrollTop = chatbotBody.scrollHeight;
}

async function chatbotSendMessage() {
    const text = chatbotInput.value.trim();
    if (!text) return;

    chatbotAppend(text, "user");
    chatbotInput.value = "";

    chatbotAppend("Đang xử lý...", "bot");
    const loading = chatbotBody.lastChild.querySelector(".chatbot-msg");

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({message: text})
        });

        const data = await response.json();
        loading.textContent = data.reply || "Không có phản hồi từ máy chủ.";

    } catch (err) {
        loading.textContent = "Lỗi khi gửi tin nhắn.";
    }
}

chatbotSend.onclick = chatbotSendMessage;

chatbotInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") chatbotSendMessage();
});

// Tin nhắn chào
chatbotAppend("Xin chào 👋! Bạn có thể hỏi về 9 loại ung thư da.", "bot");
