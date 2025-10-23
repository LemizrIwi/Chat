let ws;
let username;
let color = "#ffffff";

// Login/Register Buttons
document.getElementById("login-btn").onclick = async () => auth("/login");
document.getElementById("register-btn").onclick = async () => auth("/register");

// Enter-to-send
document.getElementById("chat-input").addEventListener("keypress", e => {
    if (e.key === "Enter") sendMessage();
});

// Farbwahl
document.getElementById("color-picker").addEventListener("input", e => {
    color = e.target.value;
});

// Auth Funktion
async function auth(route) {
    username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    const messageEl = document.getElementById("message");

    try {
        const res = await fetch(route, {
            method: "POST",
            body: new URLSearchParams({username, password})
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        // Erfolgreich
        document.getElementById("login-container").style.display = "none";
        document.getElementById("chat-container").style.display = "block";
        color = data.color;
        startWebSocket();
    } catch (err) {
        messageEl.innerText = err.message;
    }
}

// WebSocket starten
function startWebSocket() {
    ws = new WebSocket(`ws://${window.location.host}/ws`);
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        addMessage(msg);
    };
}

// Nachricht senden
document.getElementById("send-btn").onclick = sendMessage;
function sendMessage() {
    const input = document.getElementById("chat-input");
    const content = input.value.trim();
    if (!content) return;
    ws.send(JSON.stringify({ username, content, color }));
    input.value = "";
}

// Nachricht ins Chatfenster
function addMessage(msg) {
    const box = document.getElementById("chat-box");
    const div = document.createElement("div");
    div.classList.add("message");

    const time = new Date(msg.timestamp).toLocaleTimeString();
    const usernameSpan = document.createElement("span");
    usernameSpan.classList.add("username");
    if (msg.is_admin) usernameSpan.classList.add("admin");
    usernameSpan.style.color = msg.color;
    usernameSpan.innerText = msg.username;

    div.appendChild(usernameSpan);
    div.append(` [${time}]: ${msg.content}`);
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}
