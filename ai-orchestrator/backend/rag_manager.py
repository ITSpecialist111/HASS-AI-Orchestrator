"""
RAG Manager for AI Orchestrator.
Handles local vector storage (ChromaDB), embedding generation (Ollama),
and semantic search for agent context awareness.
"""
import os
import logging
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional, Any
import ollama
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class RagManager:
    """
    Manages Retrieval-Augmented Generation (RAG) capabilities.
    Stores and retrieves knowledge, entity info, and memories.
    """
    
    def __init__(
        self, 
        persist_dir: str = "/data/chroma",
        embedding_model: str = "nomic-embed-text"
    ):
        """
        Initialize RAG Manager.
        
        Args:
            persist_dir: Directory to store ChromaDB data
            embedding_model: Ollama model for generating embeddings
        """
        self.persist_dir = persist_dir
        self.embedding_model = embedding_model
        
        # Initialize ChromaDB client
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize collections
        self.knowledge_base = self.client.get_or_create_collection(
            name="knowledge_base",
            metadata={"description": "General knowledge, manuals, guides"}
        )
        
        self.entity_registry = self.client.get_or_create_collection(
            name="entity_registry",
            metadata={"description": "Home Assistant entity capabilities and details"}
        )
        
        self.memory = self.client.get_or_create_collection(
            name="memory",
            metadata={"description": "Past decisions, outcomes, and user feedback"}
        )
        
        logger.info(f"RAG Manager initialized at {persist_dir} using {embedding_model}")

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Ollama"""
        try:
            response = ollama.embeddings(model=self.embedding_model, prompt=text)
            return response["embedding"]
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector fallback or raise
            raise

    def add_document(
        self, 
        text: str, 
        collection_name: str, 
        metadata: Dict[str, Any],
        doc_id: Optional[str] = None
    ) -> str:
        """
        Add a document to the vector store.
        
        Args:
            text: Content to embed
            collection_name: 'knowledge_base', 'entity_registry', or 'memory'
            metadata: Additional info (source, timestamp, etc.)
            doc_id: Optional unique ID
            
        Returns:
            Document ID
        """
        if collection_name == "knowledge_base":
            collection = self.knowledge_base
        elif collection_name == "entity_registry":
            collection = self.entity_registry
        elif collection_name == "memory":
            collection = self.memory
        else:
            raise ValueError(f"Unknown collection: {collection_name}")
            
        if not doc_id:
            import uuid
            doc_id = str(uuid.uuid4())
            
        # Add timestamp if missing
        if "timestamp" not in metadata:
            metadata["timestamp"] = datetime.now().isoformat()
            
        # Generate embedding
        embedding = self._generate_embedding(text)
        
        # Add to Chroma
        collection.add(
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[doc_id]
        )
        
        logger.debug(f"Added document {doc_id} to {collection_name}")
        return doc_id

    def query(
        self, 
        query_text: str, 
        collection_names: List[str], 
        n_results: int = 3
    ) -> List[Dict]:
        """
        Semantic search across specified collections.
        
        Args:
            query_text: The search query
            collection_names: List of collections to search
            n_results: Number of results to return per collection
            
        Returns:
            List of result dictionaries
        """
        results = []
        query_embedding = self._generate_embedding(query_text)
        
        for name in collection_names:
            if name == "knowledge_base":
                col = self.knowledge_base
            elif name == "entity_registry":
                col = self.entity_registry
            elif name == "memory":
                col = self.memory
            else:
                continue
                
            search_res = col.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            # Format results
            if search_res["documents"]:
                for i, doc in enumerate(search_res["documents"][0]):
                    results.append({
                        "content": doc,
                        "metadata": search_res["metadatas"][0][i],
                        "distance": search_res["distances"][0][i] if search_res["distances"] else 0,
                        "source": name
                    })
        
        # Sort by relevance (distance)
        results.sort(key=lambda x: x["distance"])
        return results

    def add_memory(self, agent_id: str, decision: str, outcome: str):
        """Helper to add a decision memory"""
        text = f"Agent {agent_id} decided: {decision}. Outcome: {outcome}"
        self.add_document(
            text=text,
            collection_name="memory",
            metadata={"agent_id": agent_id, "type": "decision"}
        )
