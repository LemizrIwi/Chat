from fastapi import FastAPI, WebSocket, Request, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from datetime import datetime
import json

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Datenbank
DATABASE_URL = "sqlite:///./chat.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    color = Column(String, default="#000000")
    is_admin = Column(Boolean, default=False)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String)
    color = Column(String)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Admin automatisch anlegen
def create_admin():
    db = SessionLocal()
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        hashed = pwd_context.hash("AdminPass123!"[:72])
        admin_user = User(username="admin", password_hash=hashed, color="#ff5555", is_admin=True)
        db.add(admin_user)
        db.commit()
    db.close()

create_admin()

# WebSocket Connections
connections = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            data_json = json.loads(data)
            content = data_json.get("content")
            sender = data_json.get("sender")
            color = data_json.get("color")
            timestamp = datetime.utcnow().strftime("%H:%M:%S")

            # Nachricht speichern
            db = SessionLocal()
            msg = Message(sender=sender, color=color, content=content, timestamp=datetime.utcnow())
            db.add(msg)
            db.commit()
            db.close()

            # Nachricht an alle senden
            for conn in connections:
                await conn.send_text(json.dumps({
                    "sender": sender,
                    "color": color,
                    "content": content,
                    "timestamp": timestamp
                }))
    except:
        connections.remove(websocket)

# Login
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    if not user or not pwd_context.verify(password, user.password_hash):
        return JSONResponse({"success": False, "error": "Falscher Benutzername oder Passwort"})
    return {"success": True, "username": user.username, "color": user.color, "is_admin": user.is_admin}

# Register
@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...), color: str = Form("#000000")):
    db = SessionLocal()
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.close()
        return JSONResponse({"success": False, "error": "Benutzername existiert bereits"})
    hashed = pwd_context.hash(password[:72])
    user = User(username=username, password_hash=hashed, color=color)
    db.add(user)
    db.commit()
    db.close()
    return {"success": True, "username": username, "color": color}

# Index
@app.get("/", response_class=HTMLResponse)
async def get():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()
