let ws;
let username;
let color = "#ffffff";

// Elemente
const loginContainer = document.getElementById("login-container");
const chatContainer = document.getElementById("chat-container");
const chatBox = document.getElementById("chat-box");
const chatInput = document.getElementById("chat-input");
const messageEl = document.getElementById("message");
const colorPicker = document.getElementById("color-picker");

// Login/Register Buttons
document.getElementById("login-btn").onclick = () => auth("/login");
document.getElementById("register-btn").onclick = () => auth("/register");

// Enter-to-send
chatInput.addEventListener("keypress", e => {
    if (e.key === "Enter") sendMessage();
});

// Farbwahl
colorPicker.addEventListener("input", e => {
    color = e.target.value;
});

// Auth Funktion
async function auth(route) {
    username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    if (!username || !password) {
        messageEl.innerText = "Bitte Username und Passwort eingeben!";
        return;
    }

    try {
        const res = await fetch(route, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Fehler beim Login/Register");

        // Erfolgreich
        loginContainer.style.display = "none";
        chatContainer.style.display = "block";
        color = data.color || "#ffffff";

        startWebSocket();
    } catch (err) {
        messageEl.innerText = err.message;
    }
}

// WebSocket starten
function startWebSocket() {
    ws = new WebSocket(`ws://${window.location.host}/ws`);

    ws.onopen = () => console.log("WebSocket verbunden.");
    ws.onmessage = event => {
        const msg = JSON.parse(event.data);
        addMessage(msg);
    };
    ws.onclose = () => console.log("WebSocket getrennt.");
}

// Nachricht senden
document.getElementById("send-btn").onclick = sendMessage;
function sendMessage() {
    const content = chatInput.value.trim();
    if (!content || !ws || ws.readyState !== WebSocket.OPEN) return;

    ws.send(JSON.stringify({
        username,
        content,
        color
    }));

    chatInput.value = "";
}

// Nachricht ins Chatfenster
function addMessage(msg) {
    const div = document.createElement("div");
    div.classList.add("message");

    const time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
    
    const usernameSpan = document.createElement("span");
    usernameSpan.classList.add("username");
    if (msg.is_admin) usernameSpan.classList.add("admin");
    usernameSpan.style.color = msg.color || "#ffffff";
    usernameSpan.innerText = msg.username;

    div.appendChild(usernameSpan);
    div.append(` [${time}]: ${msg.content}`);
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}
