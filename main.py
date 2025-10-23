from fastapi import FastAPI, Request, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.hash import bcrypt
from datetime import datetime
from dotenv import load_dotenv
import os

# .env laden (für Render oder lokal)
load_dotenv()

# Datenbank
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./chat.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

app = FastAPI()

# Static & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -------------------------------------------------------------------
# Datenbankmodelle
# -------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)
    is_admin = Column(Boolean, default=False)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

# -------------------------------------------------------------------
# Admin-Erstellung (nur beim ersten Start)
# -------------------------------------------------------------------
def create_admin():
    db = SessionLocal()
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        hashed_pw = bcrypt.hash("admin")  # sicheres Hashen
        admin_user = User(username="admin", password=hashed_pw, is_admin=True)
        db.add(admin_user)
        db.commit()
        print("✅ Admin-Benutzer 'admin' mit Passwort 'admin' wurde erstellt.")
    db.close()


create_admin()

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/register")
def register(username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    if user:
        db.close()
        return JSONResponse({"success": False, "message": "Benutzername existiert bereits"})
    hashed_pw = bcrypt.hash(password)
    new_user = User(username=username, password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.close()
    return JSONResponse({"success": True, "message": "Registrierung erfolgreich"})


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    if not user or not bcrypt.verify(password, user.password):
        db.close()
        return JSONResponse({"success": False, "message": "Falscher Benutzername oder Passwort"})
    db.close()
    return JSONResponse({"success": True, "message": "Login erfolgreich"})


@app.get("/messages")
def get_messages():
    db = SessionLocal()
    messages = db.query(Message).order_by(Message.timestamp.asc()).all()
    db.close()
    return [
        {"username": msg.username, "content": msg.content, "timestamp": msg.timestamp.strftime("%H:%M:%S")}
        for msg in messages
    ]

# -------------------------------------------------------------------
# WebSocket für Chat
# -------------------------------------------------------------------

connected_clients = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            username = data["username"]
            content = data["content"]

            # Nachricht speichern
            db = SessionLocal()
            msg = Message(username=username, content=content)
            db.add(msg)
            db.commit()
            db.close()

            # Zeitstempel für Anzeige
            timestamp = datetime.utcnow().strftime("%H:%M:%S")
            message_data = {"username": username, "content": content, "timestamp": timestamp}

            # An alle verbundenen Clients senden
            for client in connected_clients:
                await client.send_json(message_data)

    except WebSocketDisconnect:
        connected_clients.remove(websocket)
        print("🔌 Client disconnected")


# -------------------------------------------------------------------
# Healthcheck (optional)
# -------------------------------------------------------------------
@app.get("/status")
def status():
    return {"status": "ok", "python": os.sys.version.split()[0]}

