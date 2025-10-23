document.addEventListener("DOMContentLoaded", () => {
    const loginContainer = document.getElementById("login-container");
    const chatContainer = document.getElementById("chat-container");
    const chatBox = document.getElementById("chat-box");
    const messageBox = document.getElementById("chat-input");
    const sendButton = document.getElementById("send-btn");
    const loginButton = document.getElementById("login-btn");
    const registerButton = document.getElementById("register-btn");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const messageElement = document.getElementById("message");
    const colorPicker = document.getElementById("color-picker");

    let username = null;

    // --- Login ---
    loginButton.addEventListener("click", async () => {
        const response = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: usernameInput.value,
                password: passwordInput.value,
            }),
        });

        const data = await response.json();
        if (response.ok) {
            username = usernameInput.value;
            loginContainer.style.display = "none";
            chatContainer.style.display = "flex";
            loadMessages();
        } else {
            messageElement.textContent = data.detail || "Fehler beim Login.";
        }
    });

    // --- Registrierung ---
    registerButton.addEventListener("click", async () => {
        const response = await fetch("/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: usernameInput.value,
                password: passwordInput.value,
            }),
        });

        const data = await response.json();
        if (response.ok) {
            messageElement.textContent = "✅ Registrierung erfolgreich. Jetzt einloggen!";
        } else {
            messageElement.textContent = data.detail || "Fehler bei der Registrierung.";
        }
    });

       // --- Nachricht senden (auch mit Enter) ---
    async function sendMessage() {
        const message = messageBox.value.trim();
        if (!message) return;

        const response = await fetch("/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: username,
                color: colorPicker.value,
                message: message,
            }),
        });

        if (response.ok) {
            messageBox.value = "";
            loadMessages();
        }
    }

    // Klick auf Button
    sendButton.addEventListener("click", sendMessage);

    // Enter-Taste drücken
    messageBox.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault(); // verhindert Zeilenumbruch
            sendMessage();
        }
    });


        if (response.ok) {
            messageBox.value = "";
            loadMessages(); // sofort aktualisieren
        }
    });

    // --- Nachrichten laden ---
    async function loadMessages() {
        const response = await fetch("/messages");
        const data = await response.json();

        chatBox.innerHTML = "";
        data.forEach(msg => {
            const msgEl = document.createElement("div");
            msgEl.classList.add("message");
            msgEl.innerHTML = `<strong style="color:${msg.color}">${msg.username}</strong>: ${msg.message}`;
            chatBox.appendChild(msgEl);
        });

        chatBox.scrollTop = chatBox.scrollHeight;
    }

    setInterval(loadMessages, 2000);
});
