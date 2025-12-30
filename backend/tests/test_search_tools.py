"""Tests for search tools (CourseSearchTool and CourseOutlineTool)"""
import pytest
import json
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchTool:
    """Tests for CourseSearchTool.execute() method"""

    def test_get_tool_definition(self, course_search_tool):
        """Test that tool definition is correct"""
        definition = course_search_tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["type"] == "object"
        assert "query" in definition["input_schema"]["properties"]
        assert "query" in definition["input_schema"]["required"]

    def test_execute_with_valid_query(self, course_search_tool, mock_vector_store):
        """Test execute with a valid query that returns results"""
        result = course_search_tool.execute(query="MCP introduction")

        # Should return formatted results
        assert isinstance(result, str)
        assert "MCP" in result or "lesson" in result.lower()

        # Verify vector store was called
        mock_vector_store.search.assert_called_once()
        call_args = mock_vector_store.search.call_args
        assert call_args[1]["query"] == "MCP introduction"

    def test_execute_with_course_filter(self, course_search_tool, mock_vector_store):
        """Test execute with course name filter"""
        result = course_search_tool.execute(
            query="introduction",
            course_name="MCP"
        )

        # Verify search was called with course_name
        mock_vector_store.search.assert_called()
        call_args = mock_vector_store.search.call_args
        assert call_args[1]["course_name"] == "MCP"

    def test_execute_with_lesson_filter(self, course_search_tool, mock_vector_store):
        """Test execute with lesson number filter"""
        result = course_search_tool.execute(
            query="introduction",
            lesson_number=1
        )

        # Verify search was called with lesson_number
        mock_vector_store.search.assert_called()
        call_args = mock_vector_store.search.call_args
        assert call_args[1]["lesson_number"] == 1

    def test_execute_returns_error_message(self, mock_vector_store):
        """Test that execute returns error message when search fails"""
        # Setup mock to return error
        mock_vector_store.search.return_value = SearchResults.empty("No course found matching 'invalid'")

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test", course_name="invalid")

        assert isinstance(result, str)
        assert "No course found" in result or "no relevant content" in result.lower()

    def test_execute_tracks_sources(self, course_search_tool):
        """Test that execute tracks sources in last_sources"""
        result = course_search_tool.execute(query="MCP introduction")

        # Should have populated last_sources
        assert hasattr(course_search_tool, 'last_sources')
        assert isinstance(course_search_tool.last_sources, list)

        # If results were found, sources should be populated
        if "No relevant content" not in result:
            assert len(course_search_tool.last_sources) > 0
            # Each source should have text and url fields
            for source in course_search_tool.last_sources:
                assert "text" in source
                assert "url" in source

    def test_execute_empty_results(self, mock_vector_store):
        """Test execute when no results are found"""
        # Setup mock to return empty results
        mock_vector_store.search.return_value = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="nonexistent topic")

        assert "No relevant content found" in result


class TestCourseOutlineTool:
    """Tests for CourseOutlineTool.execute() method"""

    def test_get_tool_definition(self, course_outline_tool):
        """Test that tool definition is correct"""
        definition = course_outline_tool.get_tool_definition()

        assert definition["name"] == "get_course_outline"
        assert "description" in definition
        assert "course_title" in definition["input_schema"]["properties"]
        assert "course_title" in definition["input_schema"]["required"]

    def test_execute_with_valid_course(self, course_outline_tool, mock_vector_store):
        """Test execute with a valid course title"""
        result = course_outline_tool.execute(course_title="MCP")

        # Should return formatted outline
        assert isinstance(result, str)
        assert "Course:" in result
        assert "Lessons" in result

        # Verify methods were called
        mock_vector_store._resolve_course_name.assert_called_once_with("MCP")
        mock_vector_store.course_catalog.get.assert_called_once()

    def test_execute_with_invalid_course(self, mock_vector_store):
        """Test execute with invalid course title"""
        # Setup mock to return None for course resolution
        mock_vector_store._resolve_course_name.return_value = None

        tool = CourseOutlineTool(mock_vector_store)
        result = tool.execute(course_title="NonexistentCourse")

        assert "No course found" in result

    def test_execute_tracks_sources(self, course_outline_tool):
        """Test that execute tracks sources"""
        result = course_outline_tool.execute(course_title="MCP")

        assert hasattr(course_outline_tool, 'last_sources')
        assert isinstance(course_outline_tool.last_sources, list)

        if "No course found" not in result:
            assert len(course_outline_tool.last_sources) > 0


class TestToolManager:
    """Tests for ToolManager"""

    def test_register_tool(self):
        """Test registering tools"""
        manager = ToolManager()
        from unittest.mock import Mock

        mock_tool = Mock()
        mock_tool.get_tool_definition.return_value = {"name": "test_tool"}

        manager.register_tool(mock_tool)

        assert "test_tool" in manager.tools

    def test_get_tool_definitions(self, tool_manager):
        """Test getting all tool definitions"""
        definitions = tool_manager.get_tool_definitions()

        assert isinstance(definitions, list)
        assert len(definitions) == 2  # search and outline tools

        names = [d["name"] for d in definitions]
        assert "search_course_content" in names
        assert "get_course_outline" in names

    def test_execute_tool_search(self, tool_manager):
        """Test executing the search tool"""
        result = tool_manager.execute_tool(
            "search_course_content",
            query="MCP introduction"
        )

        assert isinstance(result, str)

    def test_execute_tool_outline(self, tool_manager):
        """Test executing the outline tool"""
        result = tool_manager.execute_tool(
            "get_course_outline",
            course_title="MCP"
        )

        assert isinstance(result, str)
        assert "Course:" in result

    def test_execute_nonexistent_tool(self, tool_manager):
        """Test executing a tool that doesn't exist"""
        result = tool_manager.execute_tool("nonexistent_tool")

        assert "not found" in result.lower()

    def test_get_last_sources(self, tool_manager):
        """Test getting sources from last search"""
        # Execute a search
        tool_manager.execute_tool("search_course_content", query="MCP introduction")

        sources = tool_manager.get_last_sources()
        assert isinstance(sources, list)

    def test_reset_sources(self, tool_manager):
        """Test resetting sources"""
        # Execute a search to populate sources
        tool_manager.execute_tool("search_course_content", query="MCP introduction")

        # Reset sources
        tool_manager.reset_sources()

        # Sources should be empty
        sources = tool_manager.get_last_sources()
        assert sources == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
