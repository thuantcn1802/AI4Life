// static/js/chatbox.js

// 1. IMPORT FIREBASE
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { 
    getFirestore, collection, query, where, orderBy, onSnapshot, 
    addDoc, serverTimestamp, setDoc, doc, getDoc, updateDoc 
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";

// --- CẤU HÌNH FIREBASE ---
const firebaseConfig = {
    apiKey: "AIzaSyA2k5H_9RF7EMD7jwAFoO_u3NDwcGLctAg", 
    authDomain: "skincancer-a6504.firebaseapp.com",
    projectId: "skincancer-a6504",
    storageBucket: "skincancer-a6504.firebasestorage.app",
    messagingSenderId: "462483833922",
    appId: "1:462483833922:web:139c941bfab6675bde99db"
};

// Init Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

// Variables
const currentUid = window.CURRENT_UID;
let targetUid = window.TARGET_ID_FROM_URL;
let conversationId = null;
let unsubscribeMessages = null;

// DOM Elements
const msgList = document.getElementById("messagesList");
const msgInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const chatForm = document.getElementById("chatForm");
const imageInput = document.getElementById("imageInput");
const chatHeader = document.getElementById("chatHeader");
const chatUserName = document.getElementById("chatUserName");
const conversationListEl = document.getElementById("conversationList");

// ======================================================
// 1. KHỞI TẠO
// ======================================================
document.addEventListener("DOMContentLoaded", async () => {
    if (!currentUid) {
        alert("Vui lòng đăng nhập lại!");
        window.location.href = "/login";
        return;
    }
    loadSidebarConversations();
    if (targetUid) {
        await startChatWithUser(targetUid);
    }
});

// ======================================================
// 2. XỬ LÝ SIDEBAR (Giao diện mới Tailwind)
// ======================================================
function loadSidebarConversations() {
    const q = query(
        collection(db, "conversations"),
        where("participants", "array-contains", currentUid),
        orderBy("last_message_time", "desc")
    );

    onSnapshot(q, (snapshot) => {
        conversationListEl.innerHTML = ""; 
        
        if (snapshot.empty) {
            conversationListEl.innerHTML = `
                <div class="text-center mt-10">
                    <div class="bg-gray-50 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-2 text-gray-300">
                        <i class="bi bi-chat-dots"></i>
                    </div>
                    <p class="text-gray-400 text-sm">Chưa có tin nhắn nào.</p>
                </div>`;
            return;
        }

        snapshot.forEach((docSnap) => {
            const data = docSnap.data();
            const otherUid = data.participants.find(uid => uid !== currentUid);
            const isActive = otherUid === targetUid;
            
            // Tạo thẻ div cho item
            const div = document.createElement("div");
            // Tailwind classes cho item sidebar
            div.className = `p-3 rounded-xl cursor-pointer transition-all duration-200 flex items-center gap-3 border border-transparent ${
                isActive 
                ? 'bg-teal-50 border-teal-100 shadow-sm' 
                : 'hover:bg-gray-50 hover:border-gray-100'
            }`;
            
            // Nội dung HTML bên trong item
            div.innerHTML = `
                <div class="relative">
                    <div class="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-sm ${isActive ? 'bg-medical-btn' : 'bg-gray-300'}">
                        <i class="bi bi-person-fill"></i>
                    </div>
                    ${isActive ? '<span class="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-500 border-2 border-white rounded-full"></span>' : ''}
                </div>
                <div class="flex-grow overflow-hidden">
                    <div class="flex justify-between items-center mb-0.5">
                        <h4 class="font-bold text-sm text-gray-800 truncate">User: ${otherUid.slice(0,5)}...</h4>
                        <span class="text-[10px] text-gray-400">${data.last_message_time ? new Date(data.last_message_time.seconds * 1000).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : ''}</span>
                    </div>
                    <p class="text-xs text-gray-500 truncate ${isActive ? 'font-medium text-medical-dark' : ''}">
                        ${data.last_message || 'File ảnh'}
                    </p>
                </div>
            `;
            
            div.addEventListener("click", () => startChatWithUser(otherUid));
            conversationListEl.appendChild(div);
        });
    });
}

// ======================================================
// 3. XỬ LÝ LOGIC CHAT
// ======================================================
function getConversationId(uid1, uid2) {
    return uid1 < uid2 ? `${uid1}_${uid2}` : `${uid2}_${uid1}`;
}

async function startChatWithUser(uid) {
    targetUid = uid;
    conversationId = getConversationId(currentUid, targetUid);

    // Hiển thị Header & Form với style mới
    chatHeader.style.setProperty("display", "flex", "important");
    chatForm.style.setProperty("display", "flex", "important");
    
    // Update tên user
    chatUserName.innerText = `Chat với: ${uid.slice(0, 8)}...`;
    
    msgInput.disabled = false;
    sendBtn.disabled = false;
    msgInput.focus();

    // Loading state đẹp hơn
    msgList.innerHTML = `
        <div class="flex-1 flex items-center justify-center">
            <div class="flex space-x-2">
                <div class="w-2 h-2 bg-medical-btn rounded-full animate-bounce"></div>
                <div class="w-2 h-2 bg-medical-btn rounded-full animate-bounce delay-100"></div>
                <div class="w-2 h-2 bg-medical-btn rounded-full animate-bounce delay-200"></div>
            </div>
        </div>
    `;
    
    if (unsubscribeMessages) unsubscribeMessages();

    // Check & Create conversation
    const convRef = doc(db, "conversations", conversationId);
    const convSnap = await getDoc(convRef);
    if (!convSnap.exists()) {
        await setDoc(convRef, {
            participants: [currentUid, targetUid],
            last_message: "Bắt đầu cuộc trò chuyện",
            last_message_time: serverTimestamp(),
            created_at: serverTimestamp()
        });
    }

    // Listen Messages
    const messagesQuery = query(
        collection(db, "conversations", conversationId, "messages"),
        orderBy("created_at", "asc")
    );

    unsubscribeMessages = onSnapshot(messagesQuery, (snapshot) => {
        msgList.innerHTML = ""; 
        
        // Empty State
        if (snapshot.empty) {
            msgList.innerHTML = `
                <div class="flex-1 flex flex-col items-center justify-center text-center mt-10">
                    <div class="bg-gray-100 p-4 rounded-full mb-3">
                        <span class="text-2xl">👋</span>
                    </div>
                    <p class="text-gray-500 text-sm">Chưa có tin nhắn nào.<br>Hãy gửi lời chào!</p>
                </div>`;
            return;
        }

        snapshot.forEach((doc) => {
            renderMessage(doc.data());
        });

        msgList.scrollTop = msgList.scrollHeight;
    });
}

// HÀM RENDER TIN NHẮN (GIAO DIỆN MỚI TAILWIND)
function renderMessage(msg) {
    const isMine = msg.sender_id === currentUid;
    const div = document.createElement("div");
    
    // Tailwind classes cho bong bóng chat
    div.className = `flex w-full mb-4 ${isMine ? 'justify-end' : 'justify-start'}`;

    let contentHtml = "";
    if (msg.image_url) {
        contentHtml += `<img src="${msg.image_url}" class="max-w-[200px] rounded-lg mb-2 border border-gray-200 cursor-pointer hover:opacity-90 shadow-sm">`;
    }
    if (msg.text) {
        contentHtml += `<span>${msg.text}</span>`;
    }

    div.innerHTML = `
        <div class="flex flex-col ${isMine ? 'items-end' : 'items-start'} max-w-[75%]">
            <div class="px-5 py-3 rounded-2xl shadow-sm text-[15px] leading-relaxed break-words ${
                isMine 
                ? 'bg-medical-btn text-white rounded-br-none' 
                : 'bg-white border border-gray-100 text-gray-700 rounded-bl-none'
            }">
                ${contentHtml}
            </div>
            <span class="text-[10px] text-gray-400 mt-1 px-1">
                ${msg.created_at ? new Date(msg.created_at.seconds * 1000).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'Vừa xong'}
            </span>
        </div>
    `;
    
    msgList.appendChild(div);
}

// ======================================================
// 4. GỬI TIN NHẮN (Logic giữ nguyên)
// ======================================================
chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = msgInput.value.trim();
    if (!text && !imageInput.files.length) return;

    if (imageInput.files.length > 0) {
        await handleImageUpload(imageInput.files[0], text);
        chatForm.reset();
        return;
    }

    await sendMessageToFirestore(text, null);
    msgInput.value = "";
});

async function handleImageUpload(file, caption) {
    const formData = new FormData();
    formData.append("image", file);

    sendBtn.disabled = true;
    // Loading icon khi gửi ảnh
    sendBtn.innerHTML = '<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>';

    try {
        const res = await fetch("/api/chat/upload", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        
        if (data.image_url) {
            await sendMessageToFirestore(caption, data.image_url);
        } else {
            alert("Lỗi upload: " + (data.error || "Unknown"));
        }
    } catch (err) {
        console.error(err);
        alert("Lỗi kết nối server.");
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<i class="bi bi-send-fill text-lg"></i>';
    }
}

async function sendMessageToFirestore(text, imageUrl) {
    if (!conversationId) return;

    const msgData = {
        sender_id: currentUid,
        text: text || "",
        image_url: imageUrl || null,
        created_at: serverTimestamp()
    };

    await addDoc(collection(db, "conversations", conversationId, "messages"), msgData);

    const snippet = imageUrl ? "[Hình ảnh]" : text;
    await updateDoc(doc(db, "conversations", conversationId), {
        last_message: snippet,
        last_message_time: serverTimestamp()
    });
}