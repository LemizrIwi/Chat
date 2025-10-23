from fastapi import FastAPI, WebSocket, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from passlib.hash import bcrypt
from datetime import datetime
from dotenv import load_dotenv
import os
import json

# .env laden
load_dotenv()

# FastAPI Setup
app = FastAPI()

# Static + Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Datenbank Setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Usermodell
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    password_hash = Column(String)
    color = Column(String, default="#ffffff")
    is_admin = Column(Boolean, default=False)

# DB erstellen
Base.metadata.create_all(bind=engine)

# Admin automatisch erstellen
def create_admin():
    db = SessionLocal()
    if not db.query(User).filter(User.username == "admin").first():
        hashed = bcrypt.hash("admin")
        admin = User(username="admin", password_hash=hashed, color="#ff5555", is_admin=True)
        db.add(admin)
        db.commit()
        print("Admin erstellt (admin/admin)")
    db.close()

create_admin()

# Clients speichern
clients = []

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/register")
def register(username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    if db.query(User).filter(User.username == username).first():
        db.close()
        return {"detail": "Benutzername existiert bereits."}
    hashed_pw = bcrypt.hash(password)
    new_user = User(username=username, password_hash=hashed_pw)
    db.add(new_user)
    db.commit()
    db.close()
    return {"detail": "Registrierung erfolgreich!"}

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    if not user or not bcrypt.verify(password, user.password_hash):
        db.close()
        return {"detail": "Falscher Benutzername oder Passwort."}
    db.close()
    return {"username": username, "color": user.color, "is_admin": user.is_admin}

# WebSocket Chat
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg["timestamp"] = datetime.now().strftime("%H:%M:%S")
            for client in clients:
                await client.send_text(json.dumps(msg))
    except:
        clients.remove(websocket)
