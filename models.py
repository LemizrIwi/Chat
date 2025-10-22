# models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    color = Column(String, default="#FFFFFF")
    is_admin = Column(Boolean, default=False)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    content = Column(String, nullable=False)
    color = Column(String, default="#FFFFFF")
    timestamp = Column(DateTime, default=datetime.utcnow)
