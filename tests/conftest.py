"""
Pytest configuration and shared fixtures for LinkedIn Engagement Manager tests.

This module provides:
- Mock fixtures for external dependencies (OpenAI, LinkedIn API, Database)
- Common test data fixtures
- Test configuration and markers
"""

import pytest
from unittest.mock import MagicMock, patch
import os


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables to prevent import-time failures."""
    # Set required environment variables for test execution
    os.environ.setdefault("OPENAI_API_KEY", "test-api-key-12345")
    os.environ.setdefault("LI_USER", "test_user@example.com")
    os.environ.setdefault("LI_PASSWORD", "test_password")
    os.environ.setdefault("DB_HOST", "localhost")
    os.environ.setdefault("DB_USER", "test_user")
    os.environ.setdefault("DB_PASSWORD", "test_password")
    os.environ.setdefault("DB_NAME", "test_db")
    os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
    os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    os.environ.setdefault("PEXELS_API_KEY", "test-pexels-api-key-12345")


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing AI-related functions."""
    with patch("cqc_lem.utilities.ai.client.OpenAI") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        # Mock chat completions
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="Mock AI response"))]
        mock_instance.chat.completions.create.return_value = mock_completion
        
        yield mock_instance


@pytest.fixture
def mock_database_connection():
    """Mock database connection for testing database operations."""
    with patch("mysql.connector.connect") as mock_connect:
        mock_connection = MagicMock()
        mock_cursor = MagicMock()
        
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        yield {
            "connection": mock_connection,
            "cursor": mock_cursor,
        }


@pytest.fixture
def mock_selenium_driver():
    """Mock Selenium WebDriver for testing browser automation."""
    with patch("selenium.webdriver.Chrome") as mock_chrome:
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Mock common WebDriver methods
        mock_driver.get.return_value = None
        mock_driver.find_element.return_value = MagicMock()
        mock_driver.find_elements.return_value = []
        mock_driver.quit.return_value = None
        
        yield mock_driver


@pytest.fixture
def sample_linkedin_profile():
    """Sample LinkedIn profile data for testing."""
    return {
        "full_name": "John Doe",
        "job_title": "Software Engineer",
        "company_name": "Tech Company",
        "industry": "Technology",
        "profile_url": "https://www.linkedin.com/in/johndoe/",
        "mutual_connections": ["Alice Smith", "Bob Johnson"],
        "education": [
            "University of California - B.S. Computer Science (2012-2016)"
        ],
        "experiences": [],
        "skills": ["Python", "AI", "Machine Learning"],
    }


@pytest.fixture
def sample_post_data():
    """Sample post data for testing."""
    return {
        "id": 1,
        "user_id": 60,
        "content": "This is a test post about AI and automation.",
        "status": "PENDING",
        "scheduled_time": "2024-01-01 12:00:00",
        "post_type": "TEXT",
        "media_url": None,
        "video_url": None,
    }


@pytest.fixture
def sample_message_data():
    """Sample message data for testing."""
    return {
        "recipient_profile_url": "https://www.linkedin.com/in/johndoe/",
        "recipient_name": "John Doe",
        "message_content": "Hi John, I appreciate you connecting with me on LinkedIn.",
        "user_id": 60,
    }


# Marker for skipping tests that require real external services
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "requires_openai: mark test as requiring real OpenAI API access"
    )
    config.addinivalue_line(
        "markers", "requires_database: mark test as requiring real database connection"
    )
    config.addinivalue_line(
        "markers", "requires_selenium: mark test as requiring real browser automation"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
