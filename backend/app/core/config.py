from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://coderag:coderag_pass@localhost:5432/coderag"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    
    # LLM Providers
    LLM_PROVIDER: str = "ollama"  # openai, anthropic, ollama, vllm
    LLM_MODEL: str = "qwen3:latest"
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OLLAMA_URL: str = "http://localhost:11434"
    VLLM_URL: str = "http://localhost:8000"  # vLLM default URL
    
    # Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"  # Local model for Ollama setup
    EMBEDDING_DIMENSION: int = 384  # For all-MiniLM-L6-v2
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]
    
    # Projects
    PROJECTS_DIR: str = "/projects"
    
    # Logging
    LOG_PROMPTS_TO_FILE: bool = True  # Enable logging prompts to file
    LOG_PROMPTS_FILE_PATH: str = "logs/prompts.log"  # Path to prompts log file
    LOG_FAILED_ANALYSES_TO_FILE: bool = True  # Enable logging failed analyses
    LOG_FAILED_ANALYSES_FILE_PATH: str = "logs/failed_analyses.log"  # Path to failed analyses log file
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

