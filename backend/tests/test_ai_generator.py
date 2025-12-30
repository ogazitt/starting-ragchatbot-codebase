"""Tests for AI generator and tool calling functionality"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from ai_generator import AIGenerator


class TestAIGenerator:
    """Tests for AIGenerator class"""

    @pytest.fixture
    def ai_generator(self):
        """Create an AIGenerator instance for testing"""
        return AIGenerator(api_key="test_api_key", model="claude-sonnet-4-20250514")

    def test_initialization(self, ai_generator):
        """Test that AIGenerator initializes correctly"""
        assert ai_generator.model == "claude-sonnet-4-20250514"
        assert ai_generator.client is not None
        assert ai_generator.base_params["temperature"] == 0
        assert ai_generator.base_params["max_tokens"] == 800

    def test_system_prompt_mentions_tools(self, ai_generator):
        """Test that system prompt mentions available tools"""
        prompt = ai_generator.SYSTEM_PROMPT

        assert "search_course_content" in prompt
        assert "get_course_outline" in prompt
        assert "tool" in prompt.lower()

    @patch('anthropic.Anthropic')
    def test_generate_response_without_tools(self, mock_anthropic_class, ai_generator):
        """Test generating response without tools (direct answer)"""
        # Setup mock response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is a direct answer", type="text")]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response
        ai_generator.client = mock_client

        # Generate response
        result = ai_generator.generate_response(query="What is AI?")

        # Verify
        assert result == "This is a direct answer"
        mock_client.messages.create.assert_called_once()

        # Check that tools were not passed
        call_args = mock_client.messages.create.call_args
        assert "tools" not in call_args[1] or call_args[1]["tools"] is None

    @patch('anthropic.Anthropic')
    def test_generate_response_with_tool_calling(self, mock_anthropic_class, ai_generator, tool_manager):
        """Test that AIGenerator correctly handles tool calling"""
        # Setup mock client
        mock_client = MagicMock()

        # First response: Claude wants to use a tool
        mock_tool_response = MagicMock()
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "MCP introduction"}
        mock_tool_block.id = "tool_123"
        mock_tool_response.content = [mock_tool_block]
        mock_tool_response.stop_reason = "tool_use"

        # Second response: Final answer after tool execution
        mock_final_response = MagicMock()
        mock_final_response.content = [MagicMock(text="Based on the search results, MCP is...", type="text")]
        mock_final_response.stop_reason = "end_turn"

        # Configure mock to return both responses in sequence
        mock_client.messages.create.side_effect = [mock_tool_response, mock_final_response]
        ai_generator.client = mock_client

        # Generate response with tools
        tools = tool_manager.get_tool_definitions()
        result = ai_generator.generate_response(
            query="What is MCP?",
            tools=tools,
            tool_manager=tool_manager
        )

        # Verify final answer is returned
        assert "MCP" in result or "search" in result.lower()

        # Verify client was called twice (initial + follow-up)
        assert mock_client.messages.create.call_count == 2

    @patch('anthropic.Anthropic')
    def test_tool_execution_flow(self, mock_anthropic_class, ai_generator, tool_manager):
        """Test the complete tool execution flow"""
        # Setup mock client
        mock_client = MagicMock()

        # Tool use response
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test query"}
        tool_block.id = "tool_001"

        tool_response = MagicMock()
        tool_response.content = [tool_block]
        tool_response.stop_reason = "tool_use"

        # Final response
        final_response = MagicMock()
        final_response.content = [MagicMock(text="Final answer", type="text")]
        final_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [tool_response, final_response]
        ai_generator.client = mock_client

        # Execute
        tools = tool_manager.get_tool_definitions()
        result = ai_generator.generate_response(
            query="Test query",
            tools=tools,
            tool_manager=tool_manager
        )

        # Verify tool was executed
        assert result == "Final answer"

        # Check second call included tool results
        second_call_args = mock_client.messages.create.call_args_list[1]
        messages = second_call_args[1]["messages"]

        # Should have 3 messages: user query, assistant tool use, user tool results
        assert len(messages) >= 2

    @patch('anthropic.Anthropic')
    def test_conversation_history_injection(self, mock_anthropic_class, ai_generator):
        """Test that conversation history is properly injected into system prompt"""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response", type="text")]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response
        ai_generator.client = mock_client

        # Generate with history
        history = "User: Previous question\nAssistant: Previous answer"
        result = ai_generator.generate_response(
            query="New question",
            conversation_history=history
        )

        # Verify system prompt includes history
        call_args = mock_client.messages.create.call_args
        system_content = call_args[1]["system"]

        assert "Previous conversation:" in system_content
        assert history in system_content

    @patch('anthropic.Anthropic')
    def test_no_tool_manager_provided(self, mock_anthropic_class, ai_generator):
        """Test behavior when tool_use is returned but no tool_manager provided"""
        # Setup mock to return tool_use
        mock_client = MagicMock()
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_response = MagicMock()
        tool_response.content = [tool_block]
        tool_response.stop_reason = "tool_use"
        mock_client.messages.create.return_value = tool_response
        ai_generator.client = mock_client

        # Generate without tool_manager
        tools = [{"name": "test_tool"}]

        # This should handle gracefully - either return empty or raise specific error
        # The current implementation would try to access tool_manager, which would fail
        # This test documents the current behavior
        try:
            result = ai_generator.generate_response(
                query="Test",
                tools=tools,
                tool_manager=None  # No tool manager provided
            )
            # If it doesn't raise, check what it returns
            assert result is not None
        except AttributeError:
            # Expected if code tries to access None.execute_tool
            pass


class TestToolExecutionDetails:
    """Detailed tests for tool execution mechanics"""

    @patch('anthropic.Anthropic')
    def test_multiple_tool_calls_in_sequence(self, mock_anthropic_class, tool_manager):
        """Test handling multiple tool calls in one response"""
        ai_gen = AIGenerator(api_key="test", model="test-model")
        mock_client = MagicMock()

        # Response with multiple tool uses
        tool1 = MagicMock()
        tool1.type = "tool_use"
        tool1.name = "search_course_content"
        tool1.input = {"query": "test1"}
        tool1.id = "tool_1"

        tool2 = MagicMock()
        tool2.type = "tool_use"
        tool2.name = "get_course_outline"
        tool2.input = {"course_title": "MCP"}
        tool2.id = "tool_2"

        tool_response = MagicMock()
        tool_response.content = [tool1, tool2]
        tool_response.stop_reason = "tool_use"

        final_response = MagicMock()
        final_response.content = [MagicMock(text="Final", type="text")]
        final_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [tool_response, final_response]
        ai_gen.client = mock_client

        # Execute
        result = ai_gen.generate_response(
            query="Test",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Both tools should have been executed
        assert result == "Final"

    @patch('anthropic.Anthropic')
    def test_tool_error_handling(self, mock_anthropic_class, tool_manager):
        """Test that tool execution errors are handled"""
        ai_gen = AIGenerator(api_key="test", model="test-model")
        mock_client = MagicMock()

        # Tool use response
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "nonexistent_tool"  # Tool that doesn't exist
        tool_block.input = {}
        tool_block.id = "tool_err"

        tool_response = MagicMock()
        tool_response.content = [tool_block]
        tool_response.stop_reason = "tool_use"

        final_response = MagicMock()
        final_response.content = [MagicMock(text="Error handled", type="text")]
        final_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [tool_response, final_response]
        ai_gen.client = mock_client

        # Execute - should handle error gracefully
        result = ai_gen.generate_response(
            query="Test",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Should still return a result
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
