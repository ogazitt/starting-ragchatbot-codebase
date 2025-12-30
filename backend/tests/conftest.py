"""Shared test fixtures for the RAG system tests"""
import pytest
import os
import sys
from unittest.mock import Mock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
