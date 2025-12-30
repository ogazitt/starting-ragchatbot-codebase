"""Tests for RAG system end-to-end query flow"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from rag_system import RAGSystem


class TestRAGSystemQuery:
    """Tests for RAG system query method"""

    @pytest.fixture
    def mock_rag_system(self, mock_config):
        """Create a RAG system with mocked components"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.CourseSearchTool'), \
             patch('rag_system.CourseOutlineTool'):

            rag = RAGSystem(mock_config)

            # Mock the AI generator response
            rag.ai_generator.generate_response = Mock(return_value="This is the AI response")

            # Mock the tool manager
            rag.tool_manager.get_tool_definitions = Mock(return_value=[
                {"name": "search_course_content"},
                {"name": "get_course_outline"}
            ])
            rag.tool_manager.get_last_sources = Mock(return_value=[
                {"text": "MCP Course", "url": "https://example.com"}
            ])
            rag.tool_manager.reset_sources = Mock()

            # Mock session manager
            rag.session_manager.get_conversation_history = Mock(return_value=None)
            rag.session_manager.add_exchange = Mock()

            return rag

    def test_query_without_session(self, mock_rag_system):
        """Test query without providing a session ID"""
        answer, sources = mock_rag_system.query("What is MCP?")

        # Should return answer and sources
        assert isinstance(answer, str)
        assert isinstance(sources, list)
        assert answer == "This is the AI response"

        # AI generator should have been called
        mock_rag_system.ai_generator.generate_response.assert_called_once()

    def test_query_with_session(self, mock_rag_system):
        """Test query with session ID for conversation context"""
        session_id = "test_session_123"

        answer, sources = mock_rag_system.query("What is MCP?", session_id=session_id)

        # Should get conversation history
        mock_rag_system.session_manager.get_conversation_history.assert_called_once_with(session_id)

        # Should add exchange to history
        mock_rag_system.session_manager.add_exchange.assert_called_once()

    def test_query_passes_tools_to_ai(self, mock_rag_system):
        """Test that query passes tool definitions to AI generator"""
        answer, sources = mock_rag_system.query("What is MCP?")

        # Verify AI generator was called with tools
        call_args = mock_rag_system.ai_generator.generate_response.call_args
        assert "tools" in call_args[1]
        assert "tool_manager" in call_args[1]

    def test_query_retrieves_sources(self, mock_rag_system):
        """Test that query retrieves sources from tool manager"""
        answer, sources = mock_rag_system.query("What is MCP?")

        # Should get sources from tool manager
        mock_rag_system.tool_manager.get_last_sources.assert_called_once()

        # Sources should be returned
        assert len(sources) > 0
        assert sources[0]["text"] == "MCP Course"

    def test_query_resets_sources(self, mock_rag_system):
        """Test that sources are reset after retrieval"""
        answer, sources = mock_rag_system.query("What is MCP?")

        # Sources should be reset
        mock_rag_system.tool_manager.reset_sources.assert_called_once()

    def test_query_prompt_format(self, mock_rag_system):
        """Test that query is properly formatted as a prompt"""
        user_query = "What is MCP?"
        answer, sources = mock_rag_system.query(user_query)

        # Check the prompt passed to AI generator
        call_args = mock_rag_system.ai_generator.generate_response.call_args
        prompt = call_args[1]["query"]

        assert "course materials" in prompt.lower()
        assert user_query in prompt


class TestRAGSystemIntegration:
    """Integration tests for RAG system components"""

    @patch('rag_system.AIGenerator')
    @patch('rag_system.VectorStore')
    def test_content_query_triggers_search_tool(self, mock_vector_store_class, mock_ai_gen_class, mock_config):
        """Test that content-related queries trigger the search tool"""
        # This is a critical test - verifies the main user complaint

        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.CourseSearchTool') as mock_search_tool_class, \
             patch('rag_system.CourseOutlineTool'):

            # Setup mocks
            mock_ai_gen = MagicMock()
            mock_ai_gen_class.return_value = mock_ai_gen

            # Simulate AI deciding to use the search tool
            # This is what should happen for content queries
            def simulate_tool_use(query, tools, tool_manager, conversation_history=None):
                # In real scenario, AI would return tool_use stop_reason
                # and tool_manager would execute the tool
                if tools and tool_manager:
                    # Simulate tool execution
                    result = tool_manager.execute_tool(
                        "search_course_content",
                        query="MCP introduction"
                    )
                    return f"Based on the search: {result}"
                return "No tools used"

            mock_ai_gen.generate_response = Mock(side_effect=simulate_tool_use)

            # Create RAG system
            rag = RAGSystem(mock_config)

            # Override tool manager with a real one for this test
            from search_tools import ToolManager, CourseSearchTool
            from vector_store import SearchResults

            rag.tool_manager = ToolManager()

            # Create mock search tool
            mock_search_tool = Mock(spec=CourseSearchTool)
            mock_search_tool.get_tool_definition = Mock(return_value={
                "name": "search_course_content",
                "description": "Search course content"
            })
            mock_search_tool.execute = Mock(return_value="MCP search results")
            mock_search_tool.last_sources = [{"text": "MCP", "url": "http://example.com"}]

            rag.tool_manager.register_tool(mock_search_tool)

            # Execute query
            answer, sources = rag.query("What is MCP?")

            # Verify the search tool was called
            assert "search" in answer.lower() or "MCP" in answer

    @patch('rag_system.AIGenerator')
    def test_outline_query_triggers_outline_tool(self, mock_ai_gen_class, mock_config):
        """Test that outline queries trigger the outline tool"""

        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.CourseSearchTool'), \
             patch('rag_system.CourseOutlineTool'):

            mock_ai_gen = MagicMock()
            mock_ai_gen_class.return_value = mock_ai_gen

            def simulate_outline_tool_use(query, tools, tool_manager, conversation_history=None):
                if tools and tool_manager and "outline" in query.lower():
                    result = tool_manager.execute_tool(
                        "get_course_outline",
                        course_title="MCP"
                    )
                    return result
                return "No outline requested"

            mock_ai_gen.generate_response = Mock(side_effect=simulate_outline_tool_use)

            rag = RAGSystem(mock_config)

            from search_tools import ToolManager, CourseOutlineTool

            rag.tool_manager = ToolManager()

            mock_outline_tool = Mock(spec=CourseOutlineTool)
            mock_outline_tool.get_tool_definition = Mock(return_value={
                "name": "get_course_outline",
                "description": "Get course outline"
            })
            mock_outline_tool.execute = Mock(return_value="Course: MCP\nLessons:\n1. Introduction")
            mock_outline_tool.last_sources = [{"text": "MCP", "url": "http://example.com"}]

            rag.tool_manager.register_tool(mock_outline_tool)

            # Execute query
            answer, sources = rag.query("Show me the outline for MCP")

            # Verify outline tool was involved
            assert "course" in answer.lower() or "MCP" in answer


class TestRAGSystemErrorHandling:
    """Tests for error handling in RAG system"""

    @patch('rag_system.AIGenerator')
    @patch('rag_system.VectorStore')
    def test_ai_generator_exception(self, mock_vector_store_class, mock_ai_gen_class, mock_config):
        """Test handling when AI generator raises an exception"""

        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.CourseSearchTool'), \
             patch('rag_system.CourseOutlineTool'):

            mock_ai_gen = MagicMock()
            mock_ai_gen_class.return_value = mock_ai_gen

            # Make AI generator raise an exception
            mock_ai_gen.generate_response = Mock(side_effect=Exception("API Error"))

            rag = RAGSystem(mock_config)

            # Query should raise the exception
            with pytest.raises(Exception) as exc_info:
                rag.query("Test query")

            assert "API Error" in str(exc_info.value)

    @patch('rag_system.AIGenerator')
    @patch('rag_system.VectorStore')
    def test_empty_query(self, mock_vector_store_class, mock_ai_gen_class, mock_config):
        """Test handling of empty query"""

        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.CourseSearchTool'), \
             patch('rag_system.CourseOutlineTool'):

            mock_ai_gen = MagicMock()
            mock_ai_gen_class.return_value = mock_ai_gen
            mock_ai_gen.generate_response = Mock(return_value="Please provide a question")

            rag = RAGSystem(mock_config)

            # Empty query should still process
            answer, sources = rag.query("")

            # Should get some response
            assert isinstance(answer, str)


class TestRAGSystemSourceTracking:
    """Tests specifically for source tracking functionality"""

    @patch('rag_system.AIGenerator')
    @patch('rag_system.VectorStore')
    def test_sources_from_search_tool(self, mock_vector_store_class, mock_ai_gen_class, mock_config):
        """Test that sources are properly tracked from search tool"""

        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.CourseSearchTool'), \
             patch('rag_system.CourseOutlineTool'):

            rag = RAGSystem(mock_config)

            # Mock tool manager to return sources
            rag.tool_manager.get_last_sources = Mock(return_value=[
                {"text": "Source 1", "url": "http://example1.com"},
                {"text": "Source 2", "url": "http://example2.com"}
            ])

            rag.ai_generator.generate_response = Mock(return_value="Answer")

            answer, sources = rag.query("Test")

            # Should have sources
            assert len(sources) == 2
            assert sources[0]["text"] == "Source 1"

    @patch('rag_system.AIGenerator')
    @patch('rag_system.VectorStore')
    def test_sources_reset_after_query(self, mock_vector_store_class, mock_ai_gen_class, mock_config):
        """Test that sources are reset after each query"""

        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.CourseSearchTool'), \
             patch('rag_system.CourseOutlineTool'):

            rag = RAGSystem(mock_config)

            rag.tool_manager.get_last_sources = Mock(return_value=[])
            rag.tool_manager.reset_sources = Mock()
            rag.ai_generator.generate_response = Mock(return_value="Answer")

            answer, sources = rag.query("Test")

            # reset_sources should have been called
            rag.tool_manager.reset_sources.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
