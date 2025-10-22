# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from passlib.context import CryptContext
from datetime import datetime

# ------------------------------
# Datenbank Setup
# ------------------------------
DATABASE_URL = "sqlite:///michat.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ------------------------------
# Password Hashing
# ------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ------------------------------
# Models
# ------------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    color = Column(String, default="#ffffff")
    is_admin = Column(Boolean, default=False)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Tabellen erstellen
Base.metadata.create_all(bind=engine)

# ------------------------------
# FastAPI App
# ------------------------------
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------
# Pydantic Schemas
# ------------------------------
class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class MessageCreate(BaseModel):
    username: str
    content: str

# ------------------------------
# Dependency
# ------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------
# Admin User erstellen
# ------------------------------
def create_admin(db: Session):
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        hashed = pwd_context.hash("AdminPass123!"[:72])
        admin = User(username="admin", password_hash=hashed, color="#ff5555", is_admin=True)
        db.add(admin)
        db.commit()
        print("Admin erstellt: admin / AdminPass123!")

# ------------------------------
# Benutzer Register/Login
# ------------------------------
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed = pwd_context.hash(user.password[:72])
    new_user = User(username=user.username, password_hash=hashed)
    db.add(new_user)
    db.commit()
    return {"message": "User created"}

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not pwd_context.verify(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful", "username": db_user.username, "color": db_user.color}

# ------------------------------
# WebSocket Chat
# ------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg = Message(username=data["username"], content=data["content"])
            db.add(msg)
            db.commit()
            await manager.broadcast({
                "username": msg.username,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ------------------------------
# Admin erstellen beim Start
# ------------------------------
with SessionLocal() as db:
    create_admin(db)
