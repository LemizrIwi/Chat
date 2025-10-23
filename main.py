from fastapi import FastAPI, WebSocket, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from passlib.hash import bcrypt
from dotenv import load_dotenv
import os
import datetime
import json

# Load .env
load_dotenv()
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./chat.db")
SECRET_KEY = os.getenv("SECRET_KEY", "secret")

# DB Setup
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    color = Column(String, default="#ffffff")
    is_admin = Column(Boolean, default=False)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    content = Column(String)
    color = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    is_admin = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

# FastAPI App
app = FastAPI()
clients = []

# Helper functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_admin(db):
    admin_user = db.query(User).filter(User.username=="admin").first()
    if not admin_user:
        hashed = bcrypt.hash("admin")
        admin = User(username="admin", password_hash=hashed, color="#ff5555", is_admin=True)
        db.add(admin)
        db.commit()

# Initialize admin
db = next(get_db())
create_admin(db)

# Serve HTML
@app.get("/")
async def get():
    with open("index.html", "r") as f:
        return HTMLResponse(f.read())

# Auth routes
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...), db=Depends(get_db)):
    user = db.query(User).filter(User.username==username).first()
    if not user or not bcrypt.verify(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return {"username": user.username, "color": user.color, "is_admin": user.is_admin}

@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...), db=Depends(get_db)):
    if db.query(User).filter(User.username==username).first():
        raise HTTPException(status_code=400, detail="Username taken")
    hashed = bcrypt.hash(password)
    user = User(username=username, password_hash=hashed)
    db.add(user)
    db.commit()
    return {"username": user.username, "color": user.color, "is_admin": user.is_admin}

# WebSocket
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg["timestamp"] = datetime.datetime.utcnow().isoformat()
            db = next(get_db())
            db_msg = Message(
                username=msg["username"],
                content=msg["content"],
                color=msg["color"],
                is_admin=msg.get("is_admin", False)
            )
            db.add(db_msg)
            db.commit()
            # Broadcast to all clients
            for client in clients:
                await client.send_text(json.dumps(msg))
    except:
        clients.remove(websocket)
