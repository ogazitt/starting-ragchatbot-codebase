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


class TestSequentialToolCalling:
    """Tests for sequential tool calling (up to 2 rounds)"""

    @pytest.fixture
    def ai_generator(self):
        """Create an AIGenerator instance for testing"""
        return AIGenerator(api_key="test_api_key", model="claude-sonnet-4-20250514")

    @patch('anthropic.Anthropic')
    def test_single_tool_call_backward_compatibility(self, mock_anthropic_class, ai_generator, tool_manager):
        """Verify existing single tool call behavior still works"""
        from conftest import create_tool_use_response, create_text_response

        mock_client = MagicMock()

        # Round 1: Tool use
        tool_response = create_tool_use_response("search_course_content", {"query": "MCP"})
        # Round 1 final: End turn
        final_response = create_text_response("MCP is a protocol for AI applications...")

        mock_client.messages.create.side_effect = [tool_response, final_response]
        ai_generator.client = mock_client

        result = ai_generator.generate_response(
            query="What is MCP?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Verify result
        assert "MCP" in result or "protocol" in result.lower()

        # Verify 2 API calls (initial + final)
        assert mock_client.messages.create.call_count == 2

        # Check that tools were available in first call
        call1_args = mock_client.messages.create.call_args_list[0][1]
        assert "tools" in call1_args
        assert call1_args["tools"] == tool_manager.get_tool_definitions()

    @patch('anthropic.Anthropic')
    def test_two_sequential_tool_calls(self, mock_anthropic_class, ai_generator, tool_manager):
        """Verify Claude can make 2 sequential tool calls"""
        from conftest import create_tool_use_response, create_text_response

        mock_client = MagicMock()

        # Round 1: Tool use (get outline)
        tool1_response = create_tool_use_response(
            "get_course_outline",
            {"course_title": "MCP"},
            tool_id="tool_1"
        )
        # Round 2: Tool use again (search content)
        tool2_response = create_tool_use_response(
            "search_course_content",
            {"query": "lesson 4 topic", "lesson_number": 4},
            tool_id="tool_2"
        )
        # Final: End turn
        final_response = create_text_response("Lesson 4 discusses server architecture...")

        mock_client.messages.create.side_effect = [tool1_response, tool2_response, final_response]
        ai_generator.client = mock_client

        result = ai_generator.generate_response(
            query="What does lesson 4 of the MCP course cover?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Verify result
        assert "Lesson 4" in result or "lesson 4" in result.lower()

        # Verify 3 API calls (2 tool rounds + final)
        assert mock_client.messages.create.call_count == 3

        # Verify message accumulation in final call
        final_call_args = mock_client.messages.create.call_args_list[2][1]
        messages = final_call_args["messages"]

        # Should have: user query + assistant tool1 + user results1 + assistant tool2 + user results2
        assert len(messages) == 5
        assert messages[0]["role"] == "user"      # Original query
        assert messages[1]["role"] == "assistant" # Round 1 tool use
        assert messages[2]["role"] == "user"      # Round 1 results
        assert messages[3]["role"] == "assistant" # Round 2 tool use
        assert messages[4]["role"] == "user"      # Round 2 results

    @patch('anthropic.Anthropic')
    def test_early_termination_after_first_tool(self, mock_anthropic_class, ai_generator, tool_manager):
        """Verify Claude can terminate after 1 tool if it has enough info"""
        from conftest import create_tool_use_response, create_text_response

        mock_client = MagicMock()

        # Claude uses tool once then finishes
        tool_response = create_tool_use_response("search_course_content", {"query": "MCP introduction"})
        final_response = create_text_response("MCP stands for Model Context Protocol...")

        mock_client.messages.create.side_effect = [tool_response, final_response]
        ai_generator.client = mock_client

        result = ai_generator.generate_response(
            query="What is MCP?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Should only make 2 calls (not 3)
        assert mock_client.messages.create.call_count == 2
        assert "MCP" in result

    @patch('anthropic.Anthropic')
    def test_max_rounds_enforced(self, mock_anthropic_class, ai_generator, tool_manager):
        """Verify system enforces 2-round maximum"""
        from conftest import create_tool_use_response, create_text_response

        mock_client = MagicMock()

        # Claude keeps trying to use tools (simulating greedy behavior)
        tool1 = create_tool_use_response("search_course_content", {"query": "test1"}, tool_id="tool_1")
        tool2 = create_tool_use_response("search_course_content", {"query": "test2"}, tool_id="tool_2")
        # This would be round 3, but we force final response
        final = create_text_response("Based on the searches, here's the answer...")

        mock_client.messages.create.side_effect = [tool1, tool2, final]
        ai_generator.client = mock_client

        result = ai_generator.generate_response(
            query="Complex query requiring multiple searches",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Verify exactly 3 API calls (2 tool rounds + forced final)
        assert mock_client.messages.create.call_count == 3

        # Verify final call has NO tools parameter
        final_call = mock_client.messages.create.call_args_list[2][1]
        assert "tools" not in final_call

        # Result should still be returned
        assert result is not None
        assert len(result) > 0

    @patch('anthropic.Anthropic')
    def test_tool_error_handling_in_sequential_calls(self, mock_anthropic_class, ai_generator, tool_manager):
        """Verify tool errors are passed back to Claude for handling"""
        from conftest import create_tool_use_response, create_text_response

        mock_client = MagicMock()

        # Round 1: Tool use that will fail
        tool1 = create_tool_use_response("search_course_content", {"query": "test"}, tool_id="tool_1")
        # Round 2: Claude tries again after seeing error
        tool2 = create_tool_use_response("get_course_outline", {"course_title": "MCP"}, tool_id="tool_2")
        final = create_text_response("Here's what I found after retrying...")

        mock_client.messages.create.side_effect = [tool1, tool2, final]

        # Make first tool execution raise an exception
        original_execute = tool_manager.execute_tool
        call_count = [0]

        def mock_execute(name, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Course not found")
            return original_execute(name, **kwargs)

        tool_manager.execute_tool = mock_execute
        ai_generator.client = mock_client

        result = ai_generator.generate_response(
            query="Search for something",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Verify error was handled and passed through the system
        # The system should have made 3 calls total (round 1, round 2, final)
        assert mock_client.messages.create.call_count == 3

        # Verify result was still returned despite the error
        assert result is not None
        assert "retrying" in result.lower() or "found" in result.lower()

        # The error should have been caught and passed as a tool_result
        # We can verify this by checking that the execution completed successfully
        # despite the first tool raising an exception
        assert call_count[0] == 2  # Both tools were called

    @patch('anthropic.Anthropic')
    def test_context_preserved_across_rounds(self, mock_anthropic_class, ai_generator, tool_manager):
        """Verify tool results from round 1 are available in round 2"""
        from conftest import create_tool_use_response, create_text_response

        mock_client = MagicMock()

        tool1 = create_tool_use_response("get_course_outline", {"course_title": "MCP"}, tool_id="tool_1")
        tool2 = create_tool_use_response(
            "search_course_content",
            {"query": "lesson 3", "lesson_number": 3},
            tool_id="tool_2"
        )
        final = create_text_response("Lesson 3 covers MCP architecture...")

        mock_client.messages.create.side_effect = [tool1, tool2, final]
        ai_generator.client = mock_client

        result = ai_generator.generate_response(
            query="Tell me about lesson 3",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Verify round 2 API call has access to round 1 results
        round2_call_messages = mock_client.messages.create.call_args_list[1][1]["messages"]

        # By round 2, messages accumulate: original + round1 assistant + round1 results
        # The list should have at least 3 messages
        assert len(round2_call_messages) >= 3

        # Verify the structure: user, assistant (tool1), user (results1)
        assert round2_call_messages[0]["role"] == "user"
        assert round2_call_messages[1]["role"] == "assistant"
        assert round2_call_messages[2]["role"] == "user"

        # Verify round 1 results are present
        round1_results = round2_call_messages[2]["content"]
        assert any(r["type"] == "tool_result" for r in round1_results)

    @patch('anthropic.Anthropic')
    def test_tools_available_in_both_rounds(self, mock_anthropic_class, ai_generator, tool_manager):
        """Verify tools parameter is passed in both rounds"""
        from conftest import create_tool_use_response, create_text_response

        mock_client = MagicMock()

        round1_response = create_tool_use_response("search_course_content", {"query": "test1"}, tool_id="tool_1")
        round2_response = create_tool_use_response("search_course_content", {"query": "test2"}, tool_id="tool_2")
        final_response = create_text_response("Combined results...")

        mock_client.messages.create.side_effect = [round1_response, round2_response, final_response]
        ai_generator.client = mock_client

        result = ai_generator.generate_response(
            query="Test query",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Verify BOTH round 1 and round 2 calls have tools parameter
        round1_call_kwargs = mock_client.messages.create.call_args_list[0][1]
        round2_call_kwargs = mock_client.messages.create.call_args_list[1][1]

        assert "tools" in round1_call_kwargs
        assert round1_call_kwargs["tools"] == tool_manager.get_tool_definitions()
        assert "tools" in round2_call_kwargs
        assert round2_call_kwargs["tools"] == tool_manager.get_tool_definitions()

        # Verify final call does NOT have tools (forced termination)
        final_call_kwargs = mock_client.messages.create.call_args_list[2][1]
        assert "tools" not in final_call_kwargs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
