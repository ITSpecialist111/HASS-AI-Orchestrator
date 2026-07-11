
import sys
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, NonCallableMagicMock, patch
from datetime import datetime

# chromadb may fail to import on Python 3.14 + Pydantic v2 (BaseSettings moved).
# Pre-mock it so rag_manager can be imported safely in the test environment.
_mock_chromadb = MagicMock()
_mock_chromadb.PersistentClient = MagicMock
_mock_chromadb.config = MagicMock()
_mock_chromadb.config.Settings = MagicMock
sys.modules.setdefault("chromadb", _mock_chromadb)
sys.modules.setdefault("chromadb.config", _mock_chromadb.config)

from rag_manager import RagManager
from knowledge_base import KnowledgeBase
from agents.base_agent import BaseAgent
from mcp_server import MCPServer

class MockAgent(BaseAgent):
    """Mock agent for testing abstract BaseAgent"""
    async def decide(self, context): return {}
    async def gather_context(self): return {}

@pytest.fixture
def mock_chroma_client():
    """Mock ChromaDB client"""
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection

    mock_collection.query.return_value = {
        "documents": [["Test content"]],
        "metadatas": [[{"source": "test", "timestamp": "2024-01-01"}]],
        "distances": [[0.1]]
    }
    return mock_client

@pytest.fixture
def mock_ollama():
    """Mock Ollama module"""
    with patch('rag_manager.ollama') as mock:
        mock.embeddings.return_value = {"embedding": [0.1, 0.2, 0.3]}
        yield mock

@pytest.fixture
def rag_manager(mock_chroma_client, mock_ollama):
    """RagManager with mocked dependencies"""
    with patch('rag_manager.chromadb.PersistentClient', return_value=mock_chroma_client):
        manager = RagManager(persist_dir="/tmp/test_chroma")
        return manager

@pytest.mark.asyncio
async def test_rag_manager_init(rag_manager):
    """Test RAG Manager initialization"""
    assert rag_manager.client is not None
    assert rag_manager.knowledge_base is not None
    assert rag_manager.entity_registry is not None
    assert rag_manager.memory is not None

@pytest.mark.asyncio
async def test_add_document(rag_manager):
    """Test adding document to vector store"""
    doc_id = rag_manager.add_document(
        text="Test info",
        collection_name="knowledge_base",
        metadata={"source": "test"}
    )

    rag_manager.knowledge_base.add.assert_called_once()
    assert doc_id is not None

@pytest.mark.asyncio
async def test_query(rag_manager):
    """Test semantic search query"""
    results = rag_manager.query("test query", ["knowledge_base"])

    assert len(results) == 1
    assert results[0]["content"] == "Test content"
    assert results[0]["source"] == "knowledge_base"

@pytest.mark.asyncio
async def test_knowledge_base_ingest_registry(rag_manager):
    """Test HA Entity Registry ingestion"""
    mock_ha = NonCallableMagicMock()
    mock_ha.connected = True
    # Match websockets 16's ClientConnection: a live object without the
    # removed legacy ``open`` property.
    mock_ha.ws = object()
    mock_ha.get_states = AsyncMock(return_value=[
        {
            "entity_id": "light.living_room",
            "state": "on",
            "attributes": {
                "friendly_name": "Living Room Light",
                "supported_color_modes": ["rgb"]
            }
        },
        {
            "entity_id": "sensor.ignored",
            "state": "10"
        }
    ])

    kb = KnowledgeBase(rag_manager, mock_ha)
    await kb.ingest_ha_registry()

    rag_manager.entity_registry.add.assert_called()

@pytest.mark.asyncio
async def test_agent_context_retrieval(rag_manager):
    """Test Agent retrieving context"""
    mock_ha = AsyncMock()
    mock_mcp = MagicMock()

    agent = MockAgent(
        agent_id="test_agent",
        name="Test Agent",
        mcp_server=mock_mcp,
        ha_client=mock_ha,
        skills_path="dummy/path",
        rag_manager=rag_manager
    )

    context = await agent.retrieve_context("Current state is warm")

    assert "Test content" in context
    assert "[knowledge_base]" in context

@pytest.mark.asyncio
async def test_mcp_search_tool(rag_manager):
    """Test search_knowledge_base tool in MCP server"""
    mock_ha = AsyncMock()
    mcp = MCPServer(mock_ha, rag_manager=rag_manager)

    result = await mcp._search_knowledge_base({"query": "how to reset"})

    assert result["action"] == "search_knowledge_base"
    assert len(result["results"]) > 0
    assert result["results"][0]["content"] == "Test content"
