let ws;
let username;
let color = "#ffffff";

document.getElementById("login-btn").onclick = async () => auth("/login");
document.getElementById("register-btn").onclick = async () => auth("/register");

document.getElementById("chat-input").addEventListener("keypress", e => {
    if (e.key === "Enter") sendMessage();
});

document.getElementById("color-picker").addEventListener("input", e => {
    color = e.target.value;
});

async function auth(route) {
    username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    const messageEl = document.getElementById("message");

    try {
        const formData = new FormData();
        formData.append("username", username);
        formData.append("password", password);

        const res = await fetch(route, { method: "POST", body: formData });
        const data = await res.json();

        if (data.detail && data.detail.includes("Falscher")) throw new Error(data.detail);

        document.getElementById("login-container").style.display = "none";
        document.getElementById("chat-container").style.display = "block";

        if (data.color) color = data.color;
        startWebSocket();
    } catch (err) {
        messageEl.innerText = err.message;
    }
}

function startWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${protocol}://${window.location.host}/ws`);
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        addMessage(msg);
    };
}

document.getElementById("send-btn").onclick = sendMessage;

function sendMessage() {
    const input = document.getElementById("chat-input");
    const content = input.value.trim();
    if (!content) return;
    ws.send(JSON.stringify({ username, content, color }));
    input.value = "";
}

function addMessage(msg) {
    const box = document.getElementById("chat-box");
    const div = document.createElement("div");
    div.classList.add("message");

    const usernameSpan = document.createElement("span");
    usernameSpan.classList.add("username");
    if (msg.is_admin) usernameSpan.classList.add("admin");
    usernameSpan.style.color = msg.color;
    usernameSpan.innerText = msg.username;

    const time = document.createElement("span");
    time.style.color = "#888";
    time.style.marginLeft = "8px";
    time.innerText = `[${msg.timestamp}]`;

    div.appendChild(usernameSpan);
    div.appendChild(time);
    div.append(`: ${msg.content}`);
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}
