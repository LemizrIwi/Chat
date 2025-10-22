import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from db import SessionLocal, Base, engine
from models import User, Message
from typing import List

# ----------------------------
# Datenbank-Setup
# ----------------------------
Base.metadata.create_all(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# ----------------------------
# DB Session
# ----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------
# Admin erstellen (Render-safe)
# ----------------------------
def create_admin(db: Session):
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        hashed = pwd_context.hash("AdminPass123!"[:72])  # bcrypt max 72 Bytes
        admin = User(username="admin", password_hash=hashed, is_admin=1, color="#FF0000")
        db.add(admin)
        db.commit()
        print("Admin-Benutzer erstellt: admin / AdminPass123!")

db = SessionLocal()
create_admin(db)
db.close()

# ----------------------------
# Root
# ----------------------------
@app.get("/")
async def root():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "index.html not found"}

# ----------------------------
# Register
# ----------------------------
@app.post("/register")
async def register(username: str, password: str, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = pwd_context.hash(password[:72])
    user = User(username=username, password_hash=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User created"}

# ----------------------------
# Login
# ----------------------------
@app.post("/login")
async def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password[:72], user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    user.online = 1
    db.commit()
    return {"message": "Login successful", "username": user.username, "color": user.color, "is_admin": user.is_admin}

# ----------------------------
# WebSocket Manager
# ----------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

# ----------------------------
# WebSocket Endpoint
# ----------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await manager.connect(websocket)
    try:
        # Letzte 50 Nachrichten
        last_messages = db.query(Message).order_by(Message.timestamp.desc()).limit(50).all()
        for msg in reversed(last_messages):
            await websocket.send_text(json.dumps({
                "username": msg.username,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "color": "#FFFFFF"  # default, später optional User-Farbe
            }))

        # Nachrichten empfangen
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            username = payload.get("username", "Anonymous")
            content = payload.get("content", "").strip()
            color = payload.get("color", "#FFFFFF")
            if not content:
                continue

            new_msg = Message(username=username, content=content)
            db.add(new_msg)
            db.commit()
            db.refresh(new_msg)

            event = json.dumps({
                "username": new_msg.username,
                "content": new_msg.content,
                "timestamp": new_msg.timestamp.isoformat(),
                "color": color
            })
            await manager.broadcast(event)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
