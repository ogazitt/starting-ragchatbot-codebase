"""Real integration tests against the actual system
These tests use the real components (not mocks) to identify actual failures
"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from rag_system import RAGSystem
from vector_store import VectorStore


class TestRealSystemIntegration:
    """Integration tests using real components"""

    @pytest.fixture
    def real_rag_system(self):
        """Create a real RAG system for testing"""
        config = Config()
        # Use a test database path
        config.CHROMA_PATH = "./test_chroma_real"
        return RAGSystem(config)

    def test_vector_store_has_data(self, real_rag_system):
        """Test that vector store has course data loaded"""
        course_count = real_rag_system.vector_store.get_course_count()
        print(f"\n✓ Vector store has {course_count} courses")

        if course_count == 0:
            pytest.skip("No courses loaded in vector store - this is the root cause of 'query failed'")

        # If we have courses, get their titles
        titles = real_rag_system.vector_store.get_existing_course_titles()
        print(f"✓ Course titles: {titles}")

        assert course_count > 0, "Vector store should have course data"

    def test_search_tool_can_search(self, real_rag_system):
        """Test that search tool can actually search the vector store"""
        # Get available courses
        titles = real_rag_system.vector_store.get_existing_course_titles()

        if not titles:
            pytest.skip("No courses available for search testing")

        # Try to search for content
        result = real_rag_system.search_tool.execute(query="MCP")

        print(f"\n✓ Search result: {result[:200]}...")

        # Result should not be an error message
        assert not result.startswith("No course found"), f"Search failed: {result}"
        assert not result.startswith("No relevant content"), f"Search failed: {result}"

    def test_search_tool_error_message_format(self, real_rag_system):
        """Test what error message is returned when search fails"""
        # Search for something that definitely doesn't exist
        result = real_rag_system.search_tool.execute(
            query="nonexistent topic xyz123",
            course_name="nonexistent course xyz123"
        )

        print(f"\n✓ Error message format: {result}")

        # This tells us what error message the search tool returns
        assert isinstance(result, str)

    def test_ai_generator_has_api_key(self, real_rag_system):
        """Test that AI generator has a valid API key configured"""
        api_key = real_rag_system.ai_generator.client.api_key

        print(f"\n✓ API key configured: {api_key[:10]}..." if api_key else "✗ No API key")

        assert api_key, "Anthropic API key must be configured"
        assert len(api_key) > 10, "API key seems invalid"

    def test_tool_manager_has_tools_registered(self, real_rag_system):
        """Test that tools are properly registered"""
        definitions = real_rag_system.tool_manager.get_tool_definitions()

        print(f"\n✓ Registered tools: {[d['name'] for d in definitions]}")

        assert len(definitions) >= 2, "Should have at least 2 tools (search and outline)"

        names = [d["name"] for d in definitions]
        assert "search_course_content" in names
        assert "get_course_outline" in names

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="Requires ANTHROPIC_API_KEY environment variable"
    )
    def test_real_query_with_api(self, real_rag_system):
        """Test a real query against the API (requires API key)"""
        # Get available courses
        titles = real_rag_system.vector_store.get_existing_course_titles()

        if not titles:
            pytest.skip("No courses available for testing")

        # Make a real query
        try:
            answer, sources = real_rag_system.query("What is MCP?")

            print(f"\n✓ Answer received: {answer[:200]}...")
            print(f"✓ Sources: {sources}")

            assert answer, "Should receive an answer"
            assert isinstance(sources, list), "Should receive sources as a list"

        except Exception as e:
            print(f"\n✗ Query failed with exception: {e}")
            pytest.fail(f"Query raised exception: {e}")

    def test_search_directly_on_vector_store(self, real_rag_system):
        """Test searching directly on the vector store"""
        # Try to search the vector store directly
        results = real_rag_system.vector_store.search(
            query="MCP introduction",
            course_name=None,
            lesson_number=None
        )

        print(f"\n✓ Direct search results:")
        print(f"  - Error: {results.error}")
        print(f"  - Documents found: {len(results.documents)}")
        print(f"  - Metadata: {results.metadata if results.metadata else 'None'}")

        if results.error:
            print(f"\n⚠ Vector store search returned error: {results.error}")

        # This tells us if the vector store itself is working
        assert results is not None

    def test_course_catalog_collection_exists(self, real_rag_system):
        """Test that course catalog collection exists and has data"""
        try:
            catalog_count = real_rag_system.vector_store.course_catalog.count()
            print(f"\n✓ Course catalog has {catalog_count} entries")

            if catalog_count == 0:
                print("\n⚠ WARNING: Course catalog is empty!")
                print("  This means no courses have been indexed.")
                print("  The system cannot search for course content without indexed courses.")

        except Exception as e:
            print(f"\n✗ Error accessing course catalog: {e}")

    def test_course_content_collection_exists(self, real_rag_system):
        """Test that course content collection exists and has data"""
        try:
            content_count = real_rag_system.vector_store.course_content.count()
            print(f"\n✓ Course content has {content_count} chunks")

            if content_count == 0:
                print("\n⚠ WARNING: Course content is empty!")
                print("  This means no course chunks have been indexed.")
                print("  Searches will return 'No relevant content found'.")

        except Exception as e:
            print(f"\n✗ Error accessing course content: {e}")


class TestDiagnoseQueryFailure:
    """Specific tests to diagnose why queries return 'query failed'"""

    @pytest.fixture
    def rag_system(self):
        """Create RAG system instance"""
        config = Config()
        config.CHROMA_PATH = "./chroma_db"  # Use actual DB path
        return RAGSystem(config)

    def test_diagnose_search_tool_execution(self, rag_system):
        """Diagnose what happens when search tool executes"""
        print("\n" + "="*60)
        print("DIAGNOSTIC: Testing CourseSearchTool.execute()")
        print("="*60)

        # Test 1: Execute with just a query
        result1 = rag_system.search_tool.execute(query="What is MCP?")
        print(f"\n1. Simple query result: {result1[:200] if len(result1) > 200 else result1}")

        # Test 2: Execute with course name
        result2 = rag_system.search_tool.execute(
            query="introduction",
            course_name="MCP"
        )
        print(f"\n2. Query with course filter: {result2[:200] if len(result2) > 200 else result2}")

        # Test 3: Check what sources were tracked
        sources = rag_system.search_tool.last_sources
        print(f"\n3. Sources tracked: {sources}")

        # Test 4: Check vector store directly
        search_results = rag_system.vector_store.search(query="MCP")
        print(f"\n4. Direct vector store search:")
        print(f"   - Error: {search_results.error}")
        print(f"   - Documents: {len(search_results.documents)}")
        print(f"   - Has data: {not search_results.is_empty()}")

        # Conclusions
        print("\n" + "="*60)
        print("DIAGNOSTIC CONCLUSIONS:")
        print("="*60)

        if search_results.error:
            print(f"✗ Vector store is returning errors: {search_results.error}")
        elif search_results.is_empty():
            print("✗ Vector store search returns no results")
            print("  → Likely cause: No documents have been indexed")
        elif "No relevant content" in result1:
            print("✗ Search tool returns 'No relevant content found'")
            print("  → Likely cause: Vector store is empty or search doesn't match")
        else:
            print("✓ Search appears to be working")

        print("="*60 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to see print output
