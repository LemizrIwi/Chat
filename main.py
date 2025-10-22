# main.py
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from db import SessionLocal, Base, engine
from models import User, Message
from passlib.context import CryptContext
from typing import List
from datetime import datetime

# -------------------- Setup --------------------
Base.metadata.create_all(bind=engine)
app = FastAPI()

# CORS für Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -------------------- DB-Sitzung --------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------- WebSocket-Manager --------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except:
                self.disconnect(connection)

manager = ConnectionManager()

# -------------------- Login/Register --------------------
@app.post("/login")
def login(user: dict, db: Session = Depends(get_db)):
    username = user.get("username")
    password = user.get("password")
    db_user = db.query(User).filter(User.username == username).first()
    if not db_user or not pwd_context.verify(password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Benutzername oder Passwort falsch")
    return {"username": db_user.username, "color": db_user.color, "is_admin": db_user.is_admin}

@app.post("/register")
def register(user: dict, db: Session = Depends(get_db)):
    username = user.get("username")
    password = user.get("password")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Benutzer existiert bereits")
    hashed = pwd_context.hash(password[:72])  # Bcrypt Limit
    new_user = User(username=username, hashed_password=hashed, color="#FFFFFF", is_admin=False)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"username": new_user.username, "color": new_user.color, "is_admin": new_user.is_admin}

# -------------------- WebSocket --------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await manager.connect(websocket)
    try:
        # Letzte 50 Nachrichten senden
        last_messages = db.query(Message).order_by(Message.timestamp.desc()).limit(50).all()
        for msg in reversed(last_messages):
            await websocket.send_text(json.dumps({
                "username": msg.username,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "color": msg.color,
                "is_admin": msg.is_admin
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

            # Nachricht speichern
            new_msg = Message(username=username, content=content, timestamp=datetime.utcnow(),
                              color=color, is_admin=(username.lower()=="admin"))
            db.add(new_msg)
            db.commit()
            db.refresh(new_msg)

            # Nachricht an alle senden
            event = {
                "username": new_msg.username,
                "content": new_msg.content,
                "timestamp": new_msg.timestamp.isoformat(),
                "color": new_msg.color,
                "is_admin": new_msg.is_admin
            }
            await manager.broadcast(event)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

# -------------------- Admin erstellen (optional) --------------------
def create_admin(db: Session):
    if not db.query(User).filter(User.username=="admin").first():
        hashed = pwd_context.hash("AdminPass123!"[:72])
        admin = User(username="admin", hashed_password=hashed, color="#ff5555", is_admin=True)
        db.add(admin)
        db.commit()
        db.refresh(admin)

# Admin beim Start erstellen
for db in get_db():
    create_admin(db)
    break
