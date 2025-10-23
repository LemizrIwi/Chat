let ws;
let username = null;
let color = "#ffffff";

document.getElementById("login-btn").onclick = () => auth("/login");
document.getElementById("register-btn").onclick = () => auth("/register");

document.getElementById("chat-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
});

document.getElementById("color-picker").addEventListener("input", (e) => {
    color = e.target.value;
});

async function auth(route) {
    const usernameInput = document.getElementById("username").value.trim();
    const passwordInput = document.getElementById("password").value;
    const messageEl = document.getElementById("message");

    if (!usernameInput || !passwordInput) {
        messageEl.innerText = "Bitte Benutzername und Passwort eingeben.";
        return;
    }

    try {
        const res = await fetch(route, {
            method: "POST",
            body: new URLSearchParams({ username: usernameInput, password: passwordInput }),
        });
        const data = await res.json();

        if (!data.success) {
            messageEl.innerText = data.message || "Fehler beim Login/Registrieren.";
            return;
        }

        username = usernameInput;
        color = data.color || "#ffffff";

        document.getElementById("login-container").style.display = "none";
        document.getElementById("chat-container").style.display = "block";

        startWebSocket();
        loadMessages();

    } catch (err) {
        messageEl.innerText = "Verbindungsfehler: " + err.message;
    }
}

async function loadMessages() {
    const res = await fetch("/messages");
    const messages = await res.json();
    const box = document.getElementById("chat-box");
    box.innerHTML = "";
    messages.forEach(addMessage);
}

function startWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${protocol}://${window.location.host}/ws`);
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        addMessage(msg);
    };
    ws.onclose = () => console.log("🔌 Verbindung getrennt");
}

function sendMessage() {
    const input = document.getElementById("chat-input");
    const content = input.value.trim();
    if (!content || !ws) return;
    ws.send(JSON.stringify({ username, content, color }));
    input.value = "";
}

function addMessage(msg) {
    const box = document.getElementById("chat-box");
    const div = document.createElement("div");
    div.classList.add("message");

    const nameSpan = document.createElement("span");
    nameSpan.classList.add("username");
    nameSpan.style.color = msg.color || "#ffffff";
    nameSpan.innerText = msg.username;

    const time = msg.timestamp || new Date().toLocaleTimeString();

    div.appendChild(nameSpan);
    div.append(` [${time}]: ${msg.content}`);
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}
