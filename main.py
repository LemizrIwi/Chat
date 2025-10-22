from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import Column, Integer, String, Boolean, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from passlib.context import CryptContext
import os
from datetime import datetime

# --- FastAPI App ---
app = FastAPI()

# Statische Dateien bereitstellen
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Datenbank Setup ---
DATABASE_URL = "sqlite:///./michat.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# --- Password-Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Models ---
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
    username = Column(String)
    content = Column(String)
    timestamp = Column(String)

# --- Tabellen erstellen ---
Base.metadata.create_all(bind=engine)

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Admin erstellen ---
def create_admin(db: Session):
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        hashed = pwd_context.hash("AdminPass123!")  # Admin-Passwort
        admin = User(username="admin", password_hash=hashed, color="#ff5555", is_admin=True)
        db.add(admin)
        db.commit()

# Admin beim Start erstellen
with SessionLocal() as db:
    create_admin(db)

# --- Routes ---
@app.get("/")
def root():
    return FileResponse(os.path.join("static", "index.html"))

@app.post("/register")
def register(username: str, password: str, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = pwd_context.hash(password)
    user = User(username=username, password_hash=hashed)
    db.add(user)
    db.commit()
    return {"message": "User registered successfully"}

@app.post("/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "message": "Login successful",
        "username": user.username,
        "color": user.color,
        "is_admin": user.is_admin
    }

@app.get("/messages")
def get_messages(db: Session = Depends(get_db)):
    return db.query(Message).all()

@app.post("/messages")
def post_message(username: str, content: str, db: Session = Depends(get_db)):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = Message(username=username, content=content, timestamp=timestamp)
    db.add(msg)
    db.commit()
    return {"message": "Message sent"}
