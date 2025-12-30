# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Package Management

This project uses **uv** as the Python package manager. Always use uv commands:

```bash
# Install dependencies
uv sync

# Run the application
cd backend && uv run uvicorn app:app --reload --port 8000

# Quick start (from root)
./run.sh
```

**Never use pip directly** - all Python operations must go through uv.

## Project Setup

1. Ensure Python 3.13+ is installed
2. Run `uv sync` to install all dependencies (104 packages including FastAPI, ChromaDB, Anthropic SDK, sentence-transformers)
3. Create `.env` file with `ANTHROPIC_API_KEY=your_key_here`
4. Start server: `./run.sh` or manually via `cd backend && uv run uvicorn app:app --reload --port 8000`
5. Access at http://localhost:8000 (web UI) or http://localhost:8000/docs (API docs)

## Architecture Overview

### RAG Pipeline Flow

```
User Query → FastAPI → RAGSystem → AIGenerator (Claude + Tools)
                          ↓              ↓
                    SessionManager   ToolManager
                                        ↓
                                  CourseSearchTool
                                        ↓
                                   VectorStore
                                   ↙        ↘
                        ChromaDB Collections:
                        - course_catalog (metadata)
                        - course_content (chunks)
```

### Key Component Interactions

**RAGSystem (rag_system.py)** - Main orchestrator that:
- Coordinates all components (processor, vector store, AI generator, session manager, tool manager)
- Processes document ingestion via `add_course_folder()` - checks existing courses to avoid duplicates
- Handles queries via `query()` - integrates conversation history, tool-based search, and source tracking
- Provides analytics on course catalog

**AIGenerator (ai_generator.py)** - Claude API integration:
- Uses **tool calling** pattern (not direct RAG retrieval)
- Temperature=0 for consistency, max_tokens=800
- Implements agentic loop: user query → tool_use → tool execution → final response
- System prompt enforces: one search per query, no meta-commentary, brief responses
- Maintains conversation context via system messages

**ToolManager + CourseSearchTool (search_tools.py)** - Tool-based architecture:
- `CourseSearchTool` implements abstract `Tool` interface with `get_tool_definition()` and `execute()`
- Tool definition exposed to Claude for function calling
- Supports semantic course name matching (partial matches work: "MCP" finds full course)
- Optional lesson filtering via `lesson_number` parameter
- Tracks sources via `last_sources` for UI display (retrieved and reset per query)

**VectorStore (vector_store.py)** - ChromaDB wrapper:
- **Two collections**: `course_catalog` (course metadata) and `course_content` (text chunks)
- Search workflow: query → find matching course via catalog → filter content by course_id
- Uses sentence-transformers `all-MiniLM-L6-v2` for embeddings
- Returns `SearchResults` dataclass with documents, metadata, and error handling

**DocumentProcessor (document_processor.py)**:
- Extracts course metadata (title, instructor, lessons) from structured text format
- Chunks documents: 800 chars with 100 char overlap, sentence-aware splitting
- Returns `Course` object and list of `CourseChunk` objects

**SessionManager (session_manager.py)**:
- Maintains conversation history per session (max 2 message exchanges = 4 total messages)
- UUID-based session IDs
- Formats history as string for system prompt injection

### Critical Patterns

1. **Tool-Based RAG**: Claude decides when to search via tool calling, not automatic retrieval
2. **Dual ChromaDB Collections**: Course catalog enables semantic course matching before content search
3. **Idempotent Document Loading**: `add_course_folder()` checks `existing_course_titles` to skip re-processing
4. **Source Tracking**: Sources flow: `CourseSearchTool.last_sources` → `ToolManager.get_last_sources()` → `RAGSystem.query()` → API response
5. **Conversation Context**: History injected via system prompt, not as separate messages
6. **Startup Initialization**: `app.py` startup event loads docs folder automatically (non-destructive)

## Configuration (config.py)

All settings centralized in `Config` dataclass:
- Model: `claude-sonnet-4-20250514` (not claude-4)
- Embedding: `all-MiniLM-L6-v2` (sentence-transformers)
- Chunk size: 800 chars, 100 char overlap
- Max search results: 5
- Max conversation history: 2 exchanges
- ChromaDB path: `./chroma_db` (relative to backend/)

## API Endpoints

- `POST /api/query` - Submit query with optional `session_id`, returns `{answer, sources, session_id}`
- `GET /api/courses` - Get `{total_courses, course_titles}` analytics
- FastAPI auto-docs at `/docs`

## Development Notes

- **CORS enabled** (`allow_origins=["*"]`) for flexible deployment
- **No-cache headers** on static files for frontend hot-reloading
- **ChromaDB persistence**: Database created on first document load, persisted across restarts
- **Error handling**: Document processing errors print but don't crash (returns `None, 0`)
- **Frontend**: Vanilla JS (`frontend/script.js`), no build step required

## Modifying the System

**Adding a new tool**:
1. Create class extending `Tool` in `search_tools.py`
2. Implement `get_tool_definition()` (Anthropic tool schema) and `execute(**kwargs)`
3. Register in `RAGSystem.__init__()`: `self.tool_manager.register_tool(YourTool(...))`

**Changing AI behavior**:
- Edit `AIGenerator.SYSTEM_PROMPT` static variable
- Adjust `temperature` or `max_tokens` in `base_params`

**Adding document types**:
- Extend `document_processor.py` to handle new formats
- Update `add_course_folder()` file extension filter (currently `.pdf`, `.docx`, `.txt`)

**Adjusting search**:
- Modify `VectorStore.search()` parameters (similarity threshold, max results)
- Change embedding model in `config.py` (requires re-indexing)
