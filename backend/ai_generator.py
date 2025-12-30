import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to two tools for course information.

Available Tools:
1. **search_course_content** - Search for specific content within course materials
2. **get_course_outline** - Get the complete outline of a course (title, link, and all lessons)

Tool Usage Guidelines:
- Use **get_course_outline** for questions about course structure, lessons, or curriculum overview
- Use **search_course_content** for questions about specific course content or detailed educational materials
- **You may make up to 2 sequential tool calls** when needed for complex queries
- Examples requiring multiple calls:
  * Comparing content across different courses
  * Getting course outline first, then searching specific lessons
  * Multi-part questions requiring different searches
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Sequential Tool Call Strategy:
- After receiving tool results, you can decide if another tool call would help answer the query
- Common patterns:
  1. Get course outline → Search specific lesson content
  2. Search course A → Search course B → Compare results
  3. Initial search → Refined search with better parameters
- Maximum 2 tool calls total - use them wisely

Course Outline Responses:
- When using get_course_outline, include the course title, course link, and the complete lesson list
- Present each lesson with its number and title
- Format clearly for easy readability

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course outline questions**: Use get_course_outline, then present the full structure
- **Course content questions**: Use search_course_content, then answer
- **Complex queries**: Use multiple tool calls if needed (max 2)
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the tool results" or similar phrases


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # If tools available, use recursive tool calling handler
        if tools and tool_manager:
            from config import config
            return self._execute_with_tool_rounds(
                messages=[{"role": "user", "content": query}],
                system_content=system_content,
                tools=tools,
                tool_manager=tool_manager,
                current_round=0,
                max_rounds=config.MAX_TOOL_ROUNDS
            )

        # Fallback: No tools, direct response
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }

        response = self.client.messages.create(**api_params)
        return response.content[0].text
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls and get follow-up response.
        
        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            
        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name, 
                    **content_block.input
                )
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        
        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text

    def _execute_all_tools(self, content_blocks, tool_manager) -> List[Dict[str, Any]]:
        """
        Execute all tool calls from a response.

        Args:
            content_blocks: List of content blocks from Claude's response
            tool_manager: Manager to execute tools

        Returns:
            List of tool_result dicts ready to send back to Claude
        """
        tool_results = []
        for block in content_blocks:
            if block.type == "tool_use":
                try:
                    result = tool_manager.execute_tool(block.name, **block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
                except Exception as e:
                    # Pass error back to Claude as tool result
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"Error executing tool: {str(e)}",
                        "is_error": True
                    })
        return tool_results

    def _execute_with_tool_rounds(self, messages: List[Dict], system_content: str,
                                   tools: List[Dict], tool_manager,
                                   current_round: int = 0, max_rounds: int = 2) -> str:
        """
        Recursively handle tool execution rounds, allowing sequential tool calls.

        Args:
            messages: List of message dicts (user/assistant alternating)
            system_content: System prompt content
            tools: List of tool definitions
            tool_manager: Manager to execute tools
            current_round: Current round number (0-indexed)
            max_rounds: Maximum number of tool rounds allowed

        Returns:
            Final response text from Claude
        """
        # Base case: exceeded max rounds, force final response
        if current_round >= max_rounds:
            final_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content
                # No tools parameter - force Claude to provide final answer
            }
            try:
                final_response = self.client.messages.create(**final_params)
                return final_response.content[0].text
            except Exception as e:
                return f"Error getting final response: {str(e)}"

        # Make API call with tools available
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content,
            "tools": tools,
            "tool_choice": {"type": "auto"}
        }

        try:
            response = self.client.messages.create(**api_params)
        except Exception as e:
            return f"Error communicating with AI: {str(e)}"

        # Natural termination: Claude finished without tool use
        if response.stop_reason != "tool_use":
            return response.content[0].text if response.content else ""

        # Execute tools and append results to message chain
        messages.append({"role": "assistant", "content": response.content})
        tool_results = self._execute_all_tools(response.content, tool_manager)
        messages.append({"role": "user", "content": tool_results})

        # Recurse for next round
        return self._execute_with_tool_rounds(
            messages=messages,
            system_content=system_content,
            tools=tools,
            tool_manager=tool_manager,
            current_round=current_round + 1,
            max_rounds=max_rounds
        )