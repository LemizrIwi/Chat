
# main.py
import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from db import SessionLocal, Base, engine
from models import Message
from typing import List

# Datenbanktabellen erstellen (nur beim Start)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Statischer Ordner für CSS/JS/HTML
app.mount("/static", StaticFiles(directory="static"), name="static")

# Root-Endpunkt zeigt automatisch index.html
@app.get("/")
async def root():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "index.html not found"}

# WebSocket-Manager für alle Clients
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

# Datenbank-Sitzung bereitstellen
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    """Empfängt und sendet Chatnachrichten."""
    await manager.connect(websocket)
    try:
        # Letzte 50 Nachrichten an neuen Client senden
        last_messages = db.query(Message).order_by(Message.timestamp.desc()).limit(50).all()
        for msg in reversed(last_messages):
            await websocket.send_text(json.dumps({
                "username": msg.username,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }))

        # Unendliche Schleife für neue Nachrichten
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            username = payload.get("username", "Anonymous")
            content = payload.get("content", "").strip()
            if not content:
                continue

            # Nachricht speichern
            new_msg = Message(username=username, content=content)
            db.add(new_msg)
            db.commit()
            db.refresh(new_msg)

            # Nachricht an alle senden
            event = json.dumps({
                "username": new_msg.username,
                "content": new_msg.content,
                "timestamp": new_msg.timestamp.isoformat()
            })
            await manager.broadcast(event)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
