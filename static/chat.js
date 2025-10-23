document.addEventListener("DOMContentLoaded", () => {
    console.log("MiChat gestartet ✅");

    // Elemente holen
    const loginContainer = document.getElementById("login-container");
    const chatContainer = document.getElementById("chat-container");
    const loginBtn = document.getElementById("login-btn");
    const registerBtn = document.getElementById("register-btn");
    const messageBox = document.getElementById("chat-input");
    const sendButton = document.getElementById("send-btn");
    const colorPicker = document.getElementById("color-picker");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const messageElement = document.getElementById("message");

    let username = "";
    let color = "#ffffff";

    // --- Login ---
    loginBtn.addEventListener("click", async () => {
        await auth("/login");
    });

    // --- Registrierung ---
    registerBtn.addEventListener("click", async () => {
        await auth("/register");
    });

    // --- Login/Register Funktion ---
    async function auth(route) {
        const user = usernameInput.value.trim();
        const pass = passwordInput.value.trim();
        if (!user || !pass) {
            messageElement.textContent = "Bitte Benutzername und Passwort eingeben.";
            return;
        }

        try {
            const response = await fetch(route, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: user, password: pass })
            });

            let data;
            try {
                data = await response.json();
            } catch {
                data = { detail: "Fehlerhafte Serverantwort." };
            }

            if (response.ok) {
                username = user;
                color = data.color || "#ffffff";
                loginContainer.style.display = "none";
                chatContainer.style.display = "flex";
                loadMessages();
            } else {
                messageElement.textContent = data.detail || "Login fehlgeschlagen.";
                console.error("Login-Fehler:", data);
            }
        } catch (error) {
            messageElement.textContent = "Server nicht erreichbar.";
            console.error(error);
        }
    }

    // --- Nachrichten laden ---
    async function loadMessages() {
        try {
            const res = await fetch("/messages");
            const messages = await res.json();
            const chatBox = document.getElementById("chat-box");
            chatBox.innerHTML = "";

            messages.forEach(msg => {
                const div = document.createElement("div");
                div.classList.add("message");
                const time = new Date(msg.timestamp).toLocaleTimeString();

                const userSpan = document.createElement("span");
                userSpan.textContent = msg.username;
                userSpan.style.color = msg.color || "#fff";
                if (msg.is_admin) userSpan.classList.add("admin");

                div.appendChild(userSpan);
                div.append(` [${time}]: ${msg.content}`);
                chatBox.appendChild(div);
            });

            chatBox.scrollTop = chatBox.scrollHeight;
        } catch (err) {
            console.error("Fehler beim Laden der Nachrichten:", err);
        }
    }

    // --- Nachricht senden ---
    async function sendMessage() {
        const message = messageBox.value.trim();
        if (!message) return;

        try {
            const response = await fetch("/send", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    username: username,
                    color: colorPicker.value,
                    message: message
                })
            });

            if (response.ok) {
                messageBox.value = "";
                await loadMessages();
            } else {
                console.error("Fehler beim Senden:", await response.text());
            }
        } catch (error) {
            console.error("Fehler beim Senden:", error);
        }
    }

    // --- Button klick ---
    sendButton.addEventListener("click", sendMessage);

    // --- Enter drücken ---
    messageBox.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });

    // --- Automatisches Nachladen alle 3 Sekunden ---
    setInterval(loadMessages, 3000);
});
