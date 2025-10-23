from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from passlib.hash import bcrypt
from fastapi.middleware.cors import CORSMiddleware

# --- Setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Datenbank ---
DATABASE_URL = "sqlite:///./chat.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()


# --- Modelle ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    password = Column(String)
    color = Column(String, default="#ffffff")
    is_admin = Column(Boolean, default=False)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    content = Column(String)
    color = Column(String)
    is_admin = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


# --- Admin erstellen (einmalig) ---
def create_admin():
    admin_user = db.query(User).filter_by(username="admin").first()
    if not admin_user:
        admin = User(
            username="admin",
            password=bcrypt.hash("admin"),
            color="#ff0000",
            is_admin=True,
        )
        db.add(admin)
        db.commit()


create_admin()


# --- Startseite ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- Registrierung ---
@app.post("/register")
async def register(request: Request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return JSONResponse({"detail": "Fehlende Eingaben"}, status_code=400)

    user = db.query(User).filter_by(username=username).first()
    if user:
        return JSONResponse({"detail": "Benutzername existiert bereits"}, status_code=400)

    new_user = User(username=username, password=bcrypt.hash(password))
    db.add(new_user)
    db.commit()
    return {"detail": "Registrierung erfolgreich", "color": new_user.color}


# --- Login ---
@app.post("/login")
async def login(request: Request):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")

    user = db.query(User).filter_by(username=username).first()
    if not user or not bcrypt.verify(password, user.password):
        return JSONResponse({"detail": "Falscher Benutzername oder Passwort"}, status_code=400)

    return {"detail": "Login erfolgreich", "color": user.color}


# --- Nachricht senden ---
@app.post("/send")
async def send_message(request: Request):
    data = await request.json()
    username = data.get("username")
    content = data.get("message")
    color = data.get("color", "#ffffff")

    if not username or not content:
        return JSONResponse({"detail": "Ungültige Nachricht"}, status_code=400)

    user = db.query(User).filter_by(username=username).first()
    is_admin = user.is_admin if user else False

    msg = Message(username=username, content=content, color=color, is_admin=is_admin)
    db.add(msg)
    db.commit()

    return {"detail": "Nachricht gesendet"}


# --- Nachrichten abrufen ---
@app.get("/messages")
async def get_messages():
    messages = db.query(Message).order_by(Message.id.asc()).all()
    return [
        {
            "id": m.id,
            "username": m.username,
            "content": m.content,
            "color": m.color,
            "is_admin": m.is_admin,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in messages
    ]
