"""Shared test fixtures for the RAG system tests"""
import pytest
import os
import sys
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional, Union, Dict

from vector_store import VectorStore, SearchResults
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from ai_generator import AIGenerator
from rag_system import RAGSystem
from config import Config
from models import Course, Lesson, CourseChunk


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing"""
    config = Config()
    config.ANTHROPIC_API_KEY = "test_api_key"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.CHROMA_PATH = "./test_chroma_db"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.MAX_RESULTS = 5
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_HISTORY = 2
    return config


@pytest.fixture
def sample_course():
    """Create a sample course for testing"""
    return Course(
        title="MCP: Build Rich-Context AI Apps with Anthropic",
        course_link="https://www.deeplearning.ai/short-courses/mcp-build-rich-context-ai-apps-with-anthropic/",
        instructor="Test Instructor",
        lessons=[
            Lesson(lesson_number=1, title="Introduction", lesson_link="https://example.com/lesson1"),
            Lesson(lesson_number=2, title="Why MCP", lesson_link="https://example.com/lesson2"),
            Lesson(lesson_number=3, title="MCP Architecture", lesson_link="https://example.com/lesson3")
        ]
    )


@pytest.fixture
def sample_chunks(sample_course):
    """Create sample course chunks for testing"""
    return [
        CourseChunk(
            content="This is lesson 1 content about MCP introduction and basic concepts.",
            course_title=sample_course.title,
            lesson_number=1,
            chunk_index=0
        ),
        CourseChunk(
            content="This is lesson 2 content explaining why we need MCP and its benefits.",
            course_title=sample_course.title,
            lesson_number=2,
            chunk_index=1
        ),
        CourseChunk(
            content="This is lesson 3 content about MCP architecture and design patterns.",
            course_title=sample_course.title,
            lesson_number=3,
            chunk_index=2
        )
    ]


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store for testing"""
    mock_store = Mock(spec=VectorStore)

    # Mock the search method
    def mock_search(query, course_name=None, lesson_number=None, limit=None):
        # Simulate successful search
        if "MCP" in query or "introduction" in query.lower():
            return SearchResults(
                documents=["This is lesson 1 content about MCP introduction and basic concepts."],
                metadata=[{
                    "course_title": "MCP: Build Rich-Context AI Apps with Anthropic",
                    "lesson_number": 1
                }],
                distances=[0.5],
                error=None
            )
        elif course_name and "no match" in course_name.lower():
            return SearchResults.empty("No course found matching 'no match'")
        else:
            return SearchResults.empty("No relevant content found")

    mock_store.search = Mock(side_effect=mock_search)

    # Mock get_lesson_link
    mock_store.get_lesson_link = Mock(return_value="https://example.com/lesson1")

    # Mock _resolve_course_name for outline tool
    mock_store._resolve_course_name = Mock(return_value="MCP: Build Rich-Context AI Apps with Anthropic")

    # Mock course_catalog.get for outline tool
    mock_catalog = Mock()
    mock_catalog.get = Mock(return_value={
        'metadatas': [{
            'title': 'MCP: Build Rich-Context AI Apps with Anthropic',
            'course_link': 'https://www.deeplearning.ai/short-courses/mcp-build-rich-context-ai-apps-with-anthropic/',
            'lessons_json': '[{"lesson_number": 1, "lesson_title": "Introduction", "lesson_link": "https://example.com/lesson1"}, {"lesson_number": 2, "lesson_title": "Why MCP", "lesson_link": "https://example.com/lesson2"}]'
        }]
    })
    mock_store.course_catalog = mock_catalog

    return mock_store


@pytest.fixture
def course_search_tool(mock_vector_store):
    """Create a CourseSearchTool with mocked vector store"""
    return CourseSearchTool(mock_vector_store)


@pytest.fixture
def course_outline_tool(mock_vector_store):
    """Create a CourseOutlineTool with mocked vector store"""
    return CourseOutlineTool(mock_vector_store)


@pytest.fixture
def tool_manager(course_search_tool, course_outline_tool):
    """Create a ToolManager with both tools registered"""
    manager = ToolManager()
    manager.register_tool(course_search_tool)
    manager.register_tool(course_outline_tool)
    return manager


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client for testing"""
    mock_client = MagicMock()

    # Mock a successful text response (no tool use)
    mock_text_response = MagicMock()
    mock_text_response.content = [MagicMock(text="This is a test response", type="text")]
    mock_text_response.stop_reason = "end_turn"

    # Mock a tool use response
    mock_tool_response = MagicMock()
    mock_tool_block = MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.name = "search_course_content"
    mock_tool_block.input = {"query": "MCP introduction", "course_name": "MCP"}
    mock_tool_block.id = "tool_123"
    mock_tool_response.content = [mock_tool_block]
    mock_tool_response.stop_reason = "tool_use"

    # Mock final response after tool execution
    mock_final_response = MagicMock()
    mock_final_response.content = [MagicMock(text="Based on the search, MCP is about...", type="text")]
    mock_final_response.stop_reason = "end_turn"

    mock_client.messages.create = Mock(side_effect=[mock_tool_response, mock_final_response])

    return mock_client


# Helper functions for creating test responses

def create_tool_use_response(tool_name: str, tool_input: dict, tool_id: str = "tool_123"):
    """
    Helper to create a mock response with tool_use.

    Args:
        tool_name: Name of the tool to call
        tool_input: Input parameters for the tool
        tool_id: Unique ID for this tool use

    Returns:
        Mock response object with tool_use content
    """
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.input = tool_input
    tool_block.id = tool_id

    response = MagicMock()
    response.content = [tool_block]
    response.stop_reason = "tool_use"

    return response


def create_text_response(text: str):
    """
    Helper to create a mock response with text content.

    Args:
        text: The response text

    Returns:
        Mock response object with text content
    """
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text

    response = MagicMock()
    response.content = [text_block]
    response.stop_reason = "end_turn"

    return response


# API Testing Fixtures

class QueryRequest(BaseModel):
    """Request model for course queries"""
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for course queries"""
    answer: str
    sources: List[Union[str, Dict[str, Optional[str]]]]
    session_id: str


class CourseStats(BaseModel):
    """Response model for course statistics"""
    total_courses: int
    course_titles: List[str]


@pytest.fixture
def mock_rag_system():
    """Create a mock RAG system for API testing"""
    mock_rag = MagicMock(spec=RAGSystem)

    # Mock session manager
    mock_session_manager = MagicMock()
    mock_session_manager.create_session.return_value = "test-session-123"
    mock_rag.session_manager = mock_session_manager

    # Mock query method
    mock_rag.query.return_value = (
        "This is a test response about the course content.",
        [{"course": "Test Course", "lesson": "Lesson 1"}]
    )

    # Mock get_course_analytics
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["MCP Course", "AI Agents Course"]
    }

    return mock_rag


def create_test_app(mock_rag_system):
    """
    Create a test FastAPI app without static file mounting.

    This avoids the issue where the production app tries to mount
    static files from a directory that doesn't exist in tests.
    """
    from fastapi import HTTPException

    app = FastAPI(title="Course Materials RAG System - Test")

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        try:
            mock_rag_system.session_manager.clear_session(session_id)
            return {"status": "success", "message": f"Session {session_id} cleared"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        return {"message": "Course Materials RAG System API"}

    return app


@pytest.fixture
def test_app(mock_rag_system):
    """Create a test FastAPI app with mocked dependencies"""
    return create_test_app(mock_rag_system)


@pytest.fixture
def client(test_app):
    """Create a test client for the FastAPI app"""
    return TestClient(test_app)
