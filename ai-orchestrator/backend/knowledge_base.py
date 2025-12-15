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
    
            count = 0
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
                
                # Add to vector store
                self.rag.add_document(
                    text=desc,
                    collection_name="entity_registry",
                    metadata={
                        "entity_id": entity_id,
                        "domain": domain,
                        "last_updated": datetime.now().isoformat()
                    },
                    doc_id=f"entity_{entity_id}"
                )
                count += 1
                
            logger.info(f"Ingested {count} entities into Knowledge Base")
            
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
