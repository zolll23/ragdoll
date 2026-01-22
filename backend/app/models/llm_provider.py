"""LLM Provider model for managing multiple providers"""
from sqlalchemy import Column, Integer, String, JSON, Boolean, DateTime
from datetime import datetime
from app.core.database import Base


class LLMProvider(Base):
    __tablename__ = "llm_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)  # ollama, openai, anthropic, gigachat
    display_name = Column(String(100), nullable=False)
    base_url = Column(String(255))  # For custom URLs (Ollama, GigaChat)
    api_key = Column(String(512))  # Encrypted in production
    model = Column(String(100))  # Default model for this provider
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    config = Column(JSON, default=dict)  # Additional provider-specific config
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

