import logging
from typing import List
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings"""
    
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.use_local = settings.LLM_PROVIDER == "ollama" or not settings.OPENAI_API_KEY
        
        if self.use_local:
            # Use local model
            logger.info(f"Using local embedding model: {self.model_name}")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.dimension = 384
        else:
            # Use OpenAI
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.dimension = settings.EMBEDDING_DIMENSION
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        if self.use_local:
            embedding = self.model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        else:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=text
            )
            return response.data[0].embedding
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if self.use_local:
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            return embeddings.tolist()
        else:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=texts
            )
            return [item.embedding for item in response.data]

