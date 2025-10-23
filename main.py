from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from passlib.hash import bcrypt
from datetime import datetime

app = FastAPI()

# -----------------------------
# Datenbank Setup
# -----------------------------
Base = declarative_base()
DB_URL = "sqlite:///./chat.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    password = Column(String)
    color = Column(String, default="#000000")
    is_admin = Column(Boolean, default=False)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    color = Column(String)
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# -----------------------------
# Templates & Static Files
# -----------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -----------------------------
# Routen
# -----------------------------
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/register")
def register(data: dict):
    db = SessionLocal()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return JSONResponse({"detail": "Benutzername und Passwort erforderlich."}, status_code=400)

    if db.query(User).filter(User.username == username).first():
        db.close()
        return JSONResponse({"detail": "Benutzer existiert bereits."}, status_code=400)

    hashed_pw = bcrypt.hash(password)
    new_user = User(username=username, password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.close()
    return {"message": "Registrierung erfolgreich."}

@app.post("/login")
def login(data: dict):
    db = SessionLocal()
    username = data.get("username")
    password = data.get("password")

    user = db.query(User).filter(User.username == username).first()
    if not user or not bcrypt.verify(password, user.password):
        db.close()
        return JSONResponse({"detail": "Falscher Benutzername oder Passwort."}, status_code=400)

    db.close()
    return {"message": "Login erfolgreich."}

@app.post("/send")
def send_message(data: dict):
    db = SessionLocal()
    msg = Message(
        username=data.get("username"),
        color=data.get("color"),
        message=data.get("message")
    )
    db.add(msg)
    db.commit()
    db.close()
    return {"message": "OK"}

@app.get("/messages")
def get_messages():
    db = SessionLocal()
    msgs = db.query(Message).order_by(Message.timestamp.asc()).all()
    db.close()
    return [
        {"username": m.username, "color": m.color, "message": m.message, "timestamp": m.timestamp.isoformat()}
        for m in msgs
    ]
