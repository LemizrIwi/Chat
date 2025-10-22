from sqlalchemy import Column, Integer, String, DateTime, func
from db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    online = Column(Integer, default=0)  # 0=offline, 1=online
    color = Column(String, default="#FFFFFF")
    is_admin = Column(Integer, default=0)  # 1 = Admin

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    content = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
