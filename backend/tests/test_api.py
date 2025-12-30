"""Tests for FastAPI endpoints"""
import pytest
from unittest.mock import MagicMock


class TestQueryEndpoint:
    """Tests for the /api/query endpoint"""

    def test_query_success_with_new_session(self, client, mock_rag_system):
        """Test successful query creates new session when none provided"""
        response = client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "test-session-123"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_success_with_existing_session(self, client, mock_rag_system):
        """Test query uses provided session ID"""
        response = client.post(
            "/api/query",
            json={"query": "What is MCP?", "session_id": "existing-session-456"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "existing-session-456"
        mock_rag_system.session_manager.create_session.assert_not_called()
        mock_rag_system.query.assert_called_once_with(
            "What is MCP?", "existing-session-456"
        )

    def test_query_returns_answer_and_sources(self, client, mock_rag_system):
        """Test that query response includes answer and sources"""
        response = client.post(
            "/api/query",
            json={"query": "Tell me about AI agents"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "This is a test response about the course content."
        assert len(data["sources"]) == 1
        assert data["sources"][0]["course"] == "Test Course"

    def test_query_missing_query_field(self, client):
        """Test error when query field is missing"""
        response = client.post(
            "/api/query",
            json={}
        )

        assert response.status_code == 422  # Validation error

    def test_query_empty_query(self, client, mock_rag_system):
        """Test handling of empty query string"""
        response = client.post(
            "/api/query",
            json={"query": ""}
        )

        # Empty string is valid input, let the RAG system handle it
        assert response.status_code == 200

    def test_query_internal_error(self, client, mock_rag_system):
        """Test error handling when RAG system raises exception"""
        mock_rag_system.query.side_effect = Exception("Database connection failed")

        response = client.post(
            "/api/query",
            json={"query": "What is MCP?", "session_id": "test-session"}
        )

        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]


class TestCoursesEndpoint:
    """Tests for the /api/courses endpoint"""

    def test_get_courses_success(self, client, mock_rag_system):
        """Test successful retrieval of course statistics"""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 2
        assert "MCP Course" in data["course_titles"]
        assert "AI Agents Course" in data["course_titles"]

    def test_get_courses_empty(self, client, mock_rag_system):
        """Test response when no courses are loaded"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_get_courses_internal_error(self, client, mock_rag_system):
        """Test error handling when analytics fails"""
        mock_rag_system.get_course_analytics.side_effect = Exception("Vector store unavailable")

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert "Vector store unavailable" in response.json()["detail"]


class TestSessionEndpoint:
    """Tests for the /api/session endpoint"""

    def test_clear_session_success(self, client, mock_rag_system):
        """Test successful session clearing"""
        response = client.delete("/api/session/test-session-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "test-session-123" in data["message"]
        mock_rag_system.session_manager.clear_session.assert_called_once_with(
            "test-session-123"
        )

    def test_clear_session_internal_error(self, client, mock_rag_system):
        """Test error handling when session clearing fails"""
        mock_rag_system.session_manager.clear_session.side_effect = Exception(
            "Session not found"
        )

        response = client.delete("/api/session/nonexistent-session")

        assert response.status_code == 500
        assert "Session not found" in response.json()["detail"]


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_returns_message(self, client):
        """Test that root endpoint returns API message"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "RAG System" in data["message"]


class TestRequestValidation:
    """Tests for request validation"""

    def test_query_invalid_json(self, client):
        """Test handling of invalid JSON in request body"""
        response = client.post(
            "/api/query",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_query_wrong_content_type(self, client):
        """Test handling of wrong content type"""
        response = client.post(
            "/api/query",
            content="query=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 422

    def test_query_extra_fields_ignored(self, client, mock_rag_system):
        """Test that extra fields in request are ignored"""
        response = client.post(
            "/api/query",
            json={
                "query": "What is MCP?",
                "extra_field": "should be ignored",
                "another_field": 123
            }
        )

        assert response.status_code == 200


class TestResponseFormats:
    """Tests for response format validation"""

    def test_query_response_has_correct_fields(self, client, mock_rag_system):
        """Test that query response has all required fields"""
        response = client.post(
            "/api/query",
            json={"query": "test query"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check all required fields are present
        required_fields = {"answer", "sources", "session_id"}
        assert required_fields.issubset(set(data.keys()))

        # Check field types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

    def test_courses_response_has_correct_fields(self, client, mock_rag_system):
        """Test that courses response has all required fields"""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Check all required fields are present
        required_fields = {"total_courses", "course_titles"}
        assert required_fields.issubset(set(data.keys()))

        # Check field types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
