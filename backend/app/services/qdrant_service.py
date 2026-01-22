import logging
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantService:
    """Service for managing Qdrant vector database"""
    
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = "code_embeddings"
        # Use dimension from settings (384 for local models, 3072 for OpenAI)
        self.dimension = settings.EMBEDDING_DIMENSION
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
            raise
    
    def upsert_embedding(
        self,
        point_id: int,  # Qdrant accepts int or UUID
        vector: List[float],
        payload: dict
    ):
        """Insert or update embedding"""
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
        except Exception as e:
            logger.error(f"Error upserting embedding: {e}")
            raise
    
    def search(
        self,
        query_vector: List[float],
        limit: int = 10,
        filter: Optional[dict] = None
    ) -> List[dict]:
        """Search similar vectors"""
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=filter
            )
            
            return [
                {
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                }
                for result in results
            ]
        except Exception as e:
            logger.error(f"Error searching: {e}")
            return []
    
    def delete(self, point_id: int):
        """Delete embedding by ID"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[point_id]
            )
        except Exception as e:
            logger.error(f"Error deleting embedding: {e}")

