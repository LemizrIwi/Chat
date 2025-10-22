# main.py
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from db import SessionLocal, engine, Base
from models import User, Message
from passlib.context import CryptContext
from typing import List

# Passwort-Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Tabellen erstellen
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# WebSocket-Manager
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

# Datenbank-Sitzung
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Admin erstellen, falls nicht vorhanden
def create_admin(db: Session):
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        hashed = pwd_context.hash("AdminPass123!")[:72]  # Passwort max. 72 Bytes
        admin = User(username="admin", password_hash=hashed, color="#ff5555", is_admin=True)
        db.add(admin)
        db.commit()
        print("Admin erstellt!")

# Admin beim Start erstellen
db = next(get_db())
create_admin(db)

# Registrierung
@app.post("/register")
def register(username: str, password: str, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Benutzername existiert bereits")
    hashed = pwd_context.hash(password)[:72]
    user = User(username=username, password_hash=hashed, color="#FFFFFF", is_admin=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User registriert"}

# Login
@app.post("/login")
def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Benutzername oder Passwort falsch")
    return {"message": "Login erfolgreich", "username": user.username, "color": user.color}

# WebSocket-Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await manager.connect(websocket)
    try:
        # Letzte 50 Nachrichten an neuen Client
        last_messages = db.query(Message).order_by(Message.timestamp.desc()).limit(50).all()
        for msg in reversed(last_messages):
            await websocket.send_text(json.dumps({
                "username": msg.username,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "color": msg.color
            }))

        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            username = payload.get("username", "Anonymous")
            content = payload.get("content", "").strip()
            color = payload.get("color", "#FFFFFF")
            if not content:
                continue

            # Nachricht speichern
            new_msg = Message(username=username, content=content, color=color, timestamp=datetime.utcnow())
            db.add(new_msg)
            db.commit()
            db.refresh(new_msg)

            # Nachricht an alle senden
            event = json.dumps({
                "username": new_msg.username,
                "content": new_msg.content,
                "timestamp": new_msg.timestamp.isoformat(),
                "color": new_msg.color
            })
            await manager.broadcast(event)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
