"""
Knowledge Ingestion Pipeline.
Feeds data from Home Assistant and documents into the Vector Store.
"""
import logging
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from rag_manager import RagManager
from ha_client import HAWebSocketClient

logger = logging.getLogger(__name__)

class KnowledgeBase:
    """
    Manages ingestion of knowledge into the RAG system.
    """
    
    def __init__(self, rag_manager: RagManager, ha_client: HAWebSocketClient):
        self.rag = rag_manager
        self.ha = ha_client
        
    async def ingest_ha_registry(self):
        """
        Ingest Home Assistant Entity Registry.
        Learns about available devices and their capabilities.
        """
        logger.info("Starting HA Entity Registry ingestion...")
        
        try:
            # Get all states (acting as registry for now)
            # In a real scenario, we'd use the entity registry API if available
            # Use a very long timeout (5 minutes) for large installations
            states = await self.ha.get_states(timeout=300.0)
            
            # Check if states is a list (dump of all states) or single dict
            # HA WS `get_states` usually returns a list
            if isinstance(states, dict) and "result" in states:
                 # Handle raw WS response if wrapped
                 states = states["result"]
                 
            if not isinstance(states, list):
                 # Fallback if we can't get list
                 logger.warning("Could not retrieve full entity list")
                 return
    
            # Pre-fetch existing entities for delta check
            logger.info("Fetching existing vector store for delta check...")
            try:
                existing_data = self.rag.entity_registry.get(include=['metadatas'])
                existing_map = {
                    id: meta.get('desc_hash') 
                    for id, meta in zip(existing_data['ids'], existing_data['metadatas']) 
                    if meta
                }
            except Exception as e:
                logger.warning(f"Could not fetch existing data for delta check: {e}")
                existing_map = {}

            count = 0
            skipped = 0
            import hashlib
            
            for entity in states:
                entity_id = entity.get("entity_id")
                attributes = entity.get("attributes", {})
                state = entity.get("state")
                
                # Skip uninteresting entities
                domain = entity_id.split(".")[0]
                if domain not in ["climate", "light", "switch", "lock", "alarm_control_panel", "binary_sensor", "sensor"]:
                    continue
                    
                # Create semantic description
                friendly_name = attributes.get("friendly_name", entity_id)
                desc = f"Entity '{friendly_name}' ({entity_id}) is a {domain} device. "
                
                if domain == "climate":
                    modes = attributes.get("hvac_modes", [])
                    min_temp = attributes.get("min_temp")
                    max_temp = attributes.get("max_temp")
                    desc += f"It supports HVAC modes: {', '.join(modes)}. Temperature range: {min_temp}°C to {max_temp}°C."
                    
                elif domain == "light":
                    modes = attributes.get("supported_color_modes", [])
                    desc += f"Supported color modes: {', '.join(modes)}."
                    if "brightness" in attributes:
                        desc += " It supports brightness control."
                    if "color_temp" in attributes:
                        desc += " It supports color temperature control."
                
                # Compute hash for delta check
                desc_hash = hashlib.md5(desc.encode('utf-8')).hexdigest()
                doc_id = f"entity_{entity_id}"
                
                # Check cache
                if doc_id in existing_map and existing_map[doc_id] == desc_hash:
                    skipped += 1
                    continue

                # Add to vector store
                self.rag.add_document(
                    text=desc,
                    collection_name="entity_registry",
                    metadata={
                        "entity_id": entity_id,
                        "domain": domain,
                        "last_updated": datetime.now().isoformat(),
                        "desc_hash": desc_hash
                    },
                    doc_id=doc_id
                )
                count += 1
                
            logger.info(f"Ingestion complete: Added/Updated {count}, Skipped {skipped} (Unchanged)")
            
        except TimeoutError:
            logger.warning("Timed out fetching Entity Registry. Knowledge Base will be partial.")
        except Exception as e:
            logger.error(f"Error during Knowledge Base ingestion: {e}")

    async def ingest_manuals(self, manuals_dir: str = "/data/manuals"):
        """
        Ingest PDF/Markdown manuals from the data directory.
        """
        path = Path(manuals_dir)
        if not path.exists():
            return
            
        logger.info(f"Scanning {manuals_dir} for manuals...")
        
        # Support Markdown
        for md_file in path.glob("*.md"):
            with open(md_file, "r") as f:
                content = f.read()
                self.rag.add_document(
                    text=content,
                    collection_name="knowledge_base",
                    metadata={"source": md_file.name, "type": "manual"},
                    doc_id=f"manual_{md_file.stem}"
                )
                logger.info(f"Ingested manual: {md_file.name}")
                
        # Support PDF (using pypdf) - simpler placeholder for now
        # In production this would split pages/chunks
        try:
            from pypdf import PdfReader
            for pdf_file in path.glob("*.pdf"):
                reader = PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
                self.rag.add_document(
                    text=text,
                    collection_name="knowledge_base",
                    metadata={"source": pdf_file.name, "type": "manual"},
                    doc_id=f"manual_{pdf_file.stem}"
                )
                logger.info(f"Ingested PDF: {pdf_file.name}")
        except ImportError:
            logger.warning("pypdf not installed, skipping PDF ingestion")

    async def run_daily_consolidation(self):
        """Run daily tasks"""
        # Could consolidate memories here
        pass
