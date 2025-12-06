"""Vector store for semantic search."""

from typing import Optional
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer


class VectorStore:
    """Semantic search using QDRANT."""
    
    COLLECTION = "family_profiles"
    DIM = 384
    
    def __init__(self, path: str = "data/qdrant"):
        Path(path).mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=path)
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self._init_collection()
    
    def _init_collection(self):
        collections = [c.name for c in self.client.get_collections().collections]
        if self.COLLECTION not in collections:
            self.client.create_collection(
                collection_name=self.COLLECTION,
                vectors_config=VectorParams(size=self.DIM, distance=Distance.COSINE)
            )
    
    def add_person(self, person_id: int, name: str, city: str = "", 
                   interests: list = None, temples: list = None, notes: str = ""):
        """Add person to vector store."""
        text_parts = [f"Name: {name}"]
        if city:
            text_parts.append(f"City: {city}")
        if interests:
            text_parts.append(f"Interests: {', '.join(interests)}")
        if temples:
            temple_strs = [f"{t.get('name', '')} ({t.get('location', '')})" for t in temples]
            text_parts.append(f"Temples: {', '.join(temple_strs)}")
        if notes:
            text_parts.append(f"Notes: {notes}")
        
        text = ". ".join(text_parts)
        embedding = self.encoder.encode(text).tolist()
        
        self.client.upsert(
            collection_name=self.COLLECTION,
            points=[PointStruct(
                id=person_id,
                vector=embedding,
                payload={"person_id": person_id, "name": name, "text": text}
            )]
        )
    
    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Semantic search."""
        vector = self.encoder.encode(query).tolist()
        results = self.client.search(
            collection_name=self.COLLECTION,
            query_vector=vector,
            limit=limit
        )
        return [{"person_id": r.payload["person_id"], "name": r.payload["name"], 
                 "score": r.score} for r in results]
    
    def delete_person(self, person_id: int):
        """Remove person from vector store."""
        self.client.delete(collection_name=self.COLLECTION, points_selector=[person_id])
