"""
RAG Manager for AI Orchestrator.
Handles local vector storage (ChromaDB), embedding generation (Ollama),
and semantic search for agent context awareness.
"""
import os
import logging
import asyncio
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
        embedding_model: str = "nomic-embed-text",
        disable_telemetry: bool = True
    ):
        """
        Initialize RAG Manager.
        
        Args:
            persist_dir: Directory to store ChromaDB data
            embedding_model: Ollama model for generating embeddings
            disable_telemetry: Whether to opt out of ChromaDB telemetry
        """
        self.persist_dir = persist_dir
        self.embedding_model = embedding_model
        # Set to True after a confirmed successful embedding call so we
        # only attempt to ``ollama.pull`` the model once per process when
        # it's missing (issue #2).
        self._embedding_model_ready: bool = False
        self._embedding_pull_attempted: bool = False

        # Initialize ChromaDB client
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=not disable_telemetry)
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
        """Generate embedding using Ollama (sync, safe for thread executor).

        On the first ``model not found`` failure we attempt a one-shot
        ``ollama.pull`` of the configured embedding model and retry,
        so the add-on is usable out of the box without operators
        having to remember ``ollama pull nomic-embed-text`` (issue #2).
        """
        try:
            response = ollama.embeddings(model=self.embedding_model, prompt=text)
            self._embedding_model_ready = True
            return response["embedding"]
        except Exception as e:
            msg = str(e).lower()
            missing = (
                "not found" in msg
                or "no such model" in msg
                or "try pulling it" in msg
            )
            if missing and not self._embedding_pull_attempted:
                self._embedding_pull_attempted = True
                logger.warning(
                    "Embedding model %r not present locally; attempting "
                    "one-shot ollama.pull...", self.embedding_model,
                )
                try:
                    ollama.pull(self.embedding_model)
                    response = ollama.embeddings(
                        model=self.embedding_model, prompt=text
                    )
                    self._embedding_model_ready = True
                    logger.info(
                        "Embedding model %r pulled and ready.",
                        self.embedding_model,
                    )
                    return response["embedding"]
                except Exception as pull_err:
                    logger.error(
                        "Auto-pull of %r failed: %s. Run "
                        "'ollama pull %s' on the Ollama host to enable RAG.",
                        self.embedding_model, pull_err, self.embedding_model,
                    )
                    raise
            logger.error(f"Error generating embedding: {e}")
            raise

    async def _generate_embedding_async(self, text: str) -> List[float]:
        """Non-blocking wrapper — runs sync Ollama call in a thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_embedding, text)

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
