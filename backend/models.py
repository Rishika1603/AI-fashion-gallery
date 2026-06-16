from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from .database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    style_code = Column(String)
    price_min = Column(Float)
    price_max = Column(Float)
    image_url = Column(String)
    category = Column(String)
    color_swatches = Column(JSON)  # List of hex colors
    social_label = Column(String)  # e.g., "Trending", "Bestseller"
    likes = Column(Integer, default=0)
    in_stock = Column(Integer, default=1) # 1 = True, 0 = False
    embedding = Column(JSON) # Store CLIP embedding as JSON array

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    sender = Column(String) # 'user' or 'bot'
    text = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
