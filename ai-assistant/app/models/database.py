from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
from app.core.config import DATABASE_URL

# Создаем базовый класс для моделей
Base = declarative_base()

# Создаем подключение к базе данных
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Функция для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Модель клиента
class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(20), nullable=False)  # instagram, telegram, whatsapp
    platform_id = Column(String(100), nullable=False)
    username = Column(String(100), nullable=True)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Отношение один-ко-многим с сообщениями
    messages = relationship("Message", back_populates="client")
    
    # Метка для уникальности клиента по платформе и id
    __table_args__ = (
        # UniqueConstraint('platform', 'platform_id', name='unique_platform_id'),
    )

# Модель сообщения
class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    direction = Column(String(10), nullable=False)  # incoming, outgoing
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Отношение многие-к-одному с клиентом
    client = relationship("Client", back_populates="messages")

# Модель для отслеживания активности аккаунта
class AccountActivity(Base):
    __tablename__ = "account_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(20), nullable=False)  # instagram, telegram, whatsapp
    account_name = Column(String(100), nullable=False)
    action_type = Column(String(50), nullable=False)  # message_sent, login, etc.
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Мета-информация о действии
    details = Column(Text, nullable=True)
