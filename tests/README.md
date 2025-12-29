# Test Suite Documentation

This directory contains the comprehensive test suite for the LinkedIn Engagement Manager.

## Directory Structure

```
tests/
├── conftest.py              # Shared fixtures and pytest configuration
├── unit/                    # Unit tests with mocked dependencies
│   ├── app/                # Tests for application modules
│   ├── utilities/          # Tests for utility modules
│   │   ├── ai/            # AI helper tests
│   │   └── linkedin/      # LinkedIn integration tests
├── integration/            # Integration tests (multiple components)
├── e2e/                   # End-to-end tests (full workflows)
└── fixtures/              # Test data and fixtures
```

## Test Categories

### Unit Tests (`tests/unit/`)

Fast, isolated tests that verify individual functions or classes with all external dependencies mocked.

**Characteristics:**
- Run in milliseconds
- No external dependencies (database, APIs, browser)
- All dependencies mocked
- High code coverage focus

**Example:**
```python
def test_format_year():
    """Test formatting year strings."""
    assert format_year("2020") == "20"
    assert format_year("2024") == "24"
```

### Integration Tests (`tests/integration/`)

Tests that verify multiple components work together correctly.

**Characteristics:**
- May require database, Redis, or other services
- Test interactions between modules
- Slower than unit tests
- Focus on data flow and component integration

**Example:**
```python
@pytest.mark.integration
def test_engagement_workflow():
    """Test complete engagement workflow."""
    # Tests multiple components working together
    pass
```

### End-to-End Tests (`tests/e2e/`)

Tests that verify complete user workflows from start to finish.

**Characteristics:**
- Simulate real user scenarios
- May require full application stack
- Slowest test category
- Focus on business value and user experience

**Example:**
```python
@pytest.mark.e2e
def test_post_creation_and_publishing():
    """Test complete post creation and publishing workflow."""
    # Tests entire workflow
    pass
```

## Test Markers

Tests use markers to categorize and filter execution:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.requires_openai` - Requires OpenAI API access
- `@pytest.mark.requires_database` - Requires database connection
- `@pytest.mark.requires_selenium` - Requires browser automation

## Running Tests

### Basic Test Execution

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/unit/utilities/test_db.py

# Run specific test
poetry run pytest tests/unit/utilities/test_db.py::TestDatabaseOperations::test_update_db_post_status
```

### Running by Category

```bash
# Run only unit tests
poetry run pytest tests/unit -v

# Run only integration tests
poetry run pytest tests/integration -v

# Run only e2e tests
poetry run pytest tests/e2e -v
```

### Running by Marker

```bash
# Run only unit tests (using marker)
poetry run pytest -m "unit" -v

# Run tests excluding slow tests
poetry run pytest -m "not slow" -v

# Run tests that don't require external services
poetry run pytest -m "not (requires_openai or requires_database or requires_selenium)" -v
```

### Coverage Reporting

```bash
# Generate coverage report
poetry run pytest --cov=src/cqc_lem --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Test Selection

```bash
# Run tests matching pattern
poetry run pytest -k "test_database" -v

# Run tests in specific module
poetry run pytest tests/unit/utilities/ai/ -v

# Stop on first failure
poetry run pytest -x

# Run failed tests from last run
poetry run pytest --lf
```

## Fixtures

Shared fixtures are defined in `conftest.py`:

### Environment Setup

- `setup_test_environment` - Sets environment variables for tests (auto-use)

### Mock Fixtures

- `mock_openai_client` - Mocked OpenAI API client
- `mock_database_connection` - Mocked database connection
- `mock_selenium_driver` - Mocked Selenium WebDriver

### Sample Data Fixtures

- `sample_linkedin_profile` - Sample LinkedIn profile data
- `sample_post_data` - Sample post data
- `sample_message_data` - Sample message data

### Using Fixtures

```python
def test_with_fixture(sample_linkedin_profile):
    """Test using a fixture."""
    profile = LinkedInProfile(**sample_linkedin_profile)
    assert profile.full_name == "John Doe"
```

## Writing New Tests

### Test File Naming

- Use `test_*.py` pattern for test files
- Match source file names: `utilities/db.py` → `test_db.py`
- Place in appropriate directory (unit/integration/e2e)

### Test Function Naming

- Use `test_*` pattern for test functions
- Be descriptive: `test_generate_ai_response_with_valid_input`
- Avoid generic names like `test_function`

### Test Structure

Follow the Arrange-Act-Assert pattern:

```python
def test_example():
    # Arrange: Set up test data
    input_data = {"key": "value"}
    
    # Act: Execute function
    result = function_to_test(input_data)
    
    # Assert: Verify results
    assert result == expected_value
```

### Test Documentation

Always include docstrings:

```python
def test_convert_datetime_to_local_tz():
    """Test converting UTC datetime to local timezone.
    
    This test verifies that UTC datetimes are correctly
    converted to the local system timezone.
    """
    # Test implementation
```

### Mocking Guidelines

Use mocks for external dependencies:

```python
from unittest.mock import patch, MagicMock

def test_with_mock():
    """Test with mocked external dependency."""
    with patch("module.external_call") as mock_call:
        mock_call.return_value = "mocked response"
        result = function_to_test()
        assert mock_call.called
```

## Test Coverage Goals

### Current Coverage

Run `poetry run pytest --cov=src/cqc_lem --cov-report=term` to see current coverage.

### Coverage Targets

- **Minimum**: 70% for core modules
- **Target**: 85%+ for core modules
- **Critical modules**: 90%+ (db.py, ai_helper.py, scrapper.py)

### Improving Coverage

1. Identify low-coverage modules:
   ```bash
   poetry run pytest --cov=src/cqc_lem --cov-report=html
   open htmlcov/index.html
   ```

2. Add tests for uncovered lines
3. Focus on critical paths first
4. Add edge case tests
5. Verify coverage improvement

## Continuous Integration

Tests run automatically via GitHub Actions on:
- Push to `main`, `develop`, or `copilot/**` branches
- All pull requests to `main` or `develop`

CI workflow includes:
- Unit test execution
- Integration test execution (when applicable)
- Code coverage reporting
- Linting checks

## Test Maintenance

### Regular Tasks

- Keep tests updated with code changes
- Remove obsolete tests
- Refactor duplicate test code into fixtures
- Update test documentation
- Monitor and improve coverage

### When Tests Fail

1. Don't ignore failing tests
2. Investigate the root cause
3. Fix the test or the code
4. Don't skip tests to make CI pass
5. Update tests if requirements changed

## Best Practices

### DO

✅ Write tests before implementation (TDD)
✅ Keep tests independent and isolated
✅ Use descriptive test names
✅ Mock external dependencies
✅ Test edge cases and error conditions
✅ Keep tests simple and focused
✅ Use fixtures for common setup
✅ Document complex test scenarios

### DON'T

❌ Write tests that depend on other tests
❌ Use real external services in unit tests
❌ Skip or ignore failing tests
❌ Write tests without assertions
❌ Test implementation details
❌ Create overly complex test setup
❌ Forget to clean up test data

## Troubleshooting

### Common Issues

**Import Errors**
- Ensure `PYTHONPATH` includes `src`
- Check `pyproject.toml` configuration
- Verify virtual environment is activated

**Missing Dependencies**
```bash
poetry install --with test
```

**Environment Variables**
- Check `.env` file exists
- Verify required variables in `conftest.py`
- Use `setup_test_environment` fixture

**Slow Tests**
- Mark slow tests with `@pytest.mark.slow`
- Run quick tests: `pytest -m "not slow"`
- Use mocks instead of real services

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [TODO Project Timeline](../docs/TODO_PROJECT_TIMELINE.md)
- [Contributing Guidelines](../CONTRIBUTING.md)

## Questions?

If you have questions about testing:
1. Check this documentation
2. Review existing tests for examples
3. Consult TODO_PROJECT_TIMELINE.md
4. Ask in pull request or issue comments
