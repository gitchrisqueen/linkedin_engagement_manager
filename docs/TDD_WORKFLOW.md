# Test-Driven Development (TDD) Workflow

## Overview

This document describes the Test-Driven Development workflow for resolving TODO items in the LinkedIn Engagement Manager codebase. Following this workflow ensures code quality, prevents regressions, and maintains test coverage.

## Prerequisites

Before implementing any TODO item, ensure you have:

1. **Development Environment Setup:**
   ```bash
   # Clone the repository
   git clone https://github.com/gitchrisqueen/linkedin_engagement_manager.git
   cd linkedin_engagement_manager
   
   # Install dependencies
   poetry install --with test --with dev
   ```

2. **Baseline Coverage Understanding:**
   ```bash
   # Run tests and generate coverage report
   poetry run pytest --cov=src/cqc_lem --cov-report=html --cov-report=term
   
   # Open coverage report in browser
   open htmlcov/index.html  # macOS
   xdg-open htmlcov/index.html  # Linux
   ```

3. **Reviewed TODO Documentation:**
   - [TODO Project Timeline](./TODO_PROJECT_TIMELINE.md)
   - [Test Suite Documentation](../tests/README.md)

## TDD Workflow Steps

### Phase 1: Pre-Implementation (Red Phase)

#### 1.1 Identify the TODO Item
- Select a TODO item from [TODO_PROJECT_TIMELINE.md](./TODO_PROJECT_TIMELINE.md)
- Understand the business requirement and expected behavior
- Check if tests already exist for the feature

#### 1.2 Write Failing Tests
Before implementing any code changes, write tests that demonstrate the current broken/missing behavior.

**Example: TODO in scrapper.py - "Fix for when prefix is empty"**

```python
# tests/unit/utilities/linkedin/test_scrapper.py

import pytest
from cqc_lem.utilities.linkedin.scrapper import LinkedInProfile

class TestScraperEdgeCases:
    """Test edge cases for LinkedIn scraper."""
    
    def test_handle_empty_prefix(self):
        """Test that scraper handles empty prefix correctly.
        
        Current behavior: Fails when prefix is empty
        Expected behavior: Returns valid profile data with no prefix
        """
        # Arrange
        profile_data = {
            "full_name": "John Doe",
            "job_title": "Software Engineer",
            "prefix": "",  # Empty prefix - this is the edge case
        }
        
        # Act
        profile = LinkedInProfile(**profile_data)
        
        # Assert
        assert profile.full_name == "John Doe"
        assert profile.prefix == ""  # Should handle empty string
        # This test will FAIL initially if the bug exists
```

**Run the test to confirm it fails:**
```bash
poetry run pytest tests/unit/utilities/linkedin/test_scrapper.py::TestScraperEdgeCases::test_handle_empty_prefix -v
```

Expected output: `FAILED` ❌

#### 1.3 Document Test Scenarios
Create a test file header documenting all scenarios:

```python
"""
Test Suite: LinkedIn Scraper - Empty Prefix Handling

TODO Reference: TODO_PROJECT_TIMELINE.md - Group 1, Item 2
File: src/cqc_lem/utilities/linkedin/scrapper.py:238

Test Scenarios:
1. ✅ Normal prefix handling (existing test)
2. ❌ Empty string prefix (new test - currently failing)
3. ❌ None prefix value (new test - currently failing)
4. ✅ Whitespace prefix handling (new test)

Coverage Target: Increase scrapper.py from 10% to 70%+
"""
```

### Phase 2: Implementation (Green Phase)

#### 2.1 Implement Minimum Code to Pass Tests
Write the minimal code needed to make the failing test pass.

**Example:**
```python
# src/cqc_lem/utilities/linkedin/scrapper.py

class LinkedInProfile:
    def __init__(self, **kwargs):
        # Fix: Handle empty prefix
        self.prefix = kwargs.get('prefix', '').strip() if kwargs.get('prefix') else ''
        self.full_name = kwargs.get('full_name', '')
        # ... rest of initialization
```

#### 2.2 Run Tests Iteratively
```bash
# Run only the specific test you're working on
poetry run pytest tests/unit/utilities/linkedin/test_scrapper.py::TestScraperEdgeCases -v

# Run all scrapper tests
poetry run pytest tests/unit/utilities/linkedin/test_scrapper.py -v

# Run all unit tests
poetry run pytest tests/unit -v
```

Expected output: `PASSED` ✅

#### 2.3 Verify No Regressions
```bash
# Run full test suite
poetry run pytest tests/ -v

# Check that no existing tests broke
# All tests should pass: XX passed, 0 failed
```

### Phase 3: Refactoring (Refactor Phase)

#### 3.1 Improve Code Quality
While keeping tests passing, refactor for:
- Code clarity
- Performance
- Consistency with codebase patterns
- Type hints and documentation

```python
# Improved version with type hints
from typing import Optional

class LinkedInProfile:
    def __init__(self, **kwargs):
        self.prefix: str = self._normalize_prefix(kwargs.get('prefix'))
        # ... rest of initialization
    
    def _normalize_prefix(self, prefix: Optional[str]) -> str:
        """Normalize prefix string, handling empty and None values.
        
        Args:
            prefix: The prefix string from profile data
            
        Returns:
            Normalized prefix string (empty string if None or empty)
        """
        if not prefix:
            return ''
        return prefix.strip()
```

#### 3.2 Run Tests After Each Refactoring
```bash
poetry run pytest tests/unit/utilities/linkedin/ -v

# All tests should still pass after refactoring
```

### Phase 4: Coverage Validation

#### 4.1 Check Coverage Improvement
```bash
# Generate coverage report
poetry run pytest --cov=src/cqc_lem --cov-report=term --cov-report=html

# Check specific module coverage
poetry run pytest --cov=src/cqc_lem/utilities/linkedin/scrapper --cov-report=term
```

**Verify:**
- Coverage increased for the modified module
- No coverage decreased in other modules
- Module meets minimum 70% threshold (or is progressing toward it)

#### 4.2 Add Additional Edge Case Tests
If coverage is still below target, identify uncovered lines:

```bash
# View detailed coverage report
open htmlcov/src_cqc_lem_utilities_linkedin_scrapper_py.html
```

Add tests for uncovered lines:
```python
class TestScraperEdgeCases:
    def test_handle_none_prefix(self):
        """Test scraper with None prefix value."""
        profile = LinkedInProfile(full_name="Jane Doe", prefix=None)
        assert profile.prefix == ""
    
    def test_handle_whitespace_prefix(self):
        """Test scraper with whitespace-only prefix."""
        profile = LinkedInProfile(full_name="Jane Doe", prefix="   ")
        assert profile.prefix == ""
```

### Phase 5: Documentation and Commit

#### 5.1 Update Documentation
- Update docstrings with clear descriptions
- Add inline comments for complex logic
- Update TODO_PROJECT_TIMELINE.md to mark item as complete

#### 5.2 Commit with Clear Message
```bash
# Stage changes
git add src/cqc_lem/utilities/linkedin/scrapper.py
git add tests/unit/utilities/linkedin/test_scrapper.py

# Commit with descriptive message
git commit -m "Fix empty prefix handling in LinkedIn scraper

- Add validation for empty and None prefix values
- Normalize whitespace in prefix strings
- Add comprehensive tests for edge cases
- Increase scrapper.py coverage from 10% to 25%

Resolves: TODO_PROJECT_TIMELINE.md - Group 1, Item 2
Tests: tests/unit/utilities/linkedin/test_scrapper.py::TestScraperEdgeCases"
```

### Phase 6: CI/CD Validation

#### 6.1 Push and Monitor CI
```bash
# Push to feature branch
git push origin feature/fix-empty-prefix

# Create pull request
# Monitor GitHub Actions CI/CD pipeline
```

**CI Checks:**
- ✅ All unit tests pass
- ✅ Coverage threshold met (70% minimum on changed files)
- ✅ Linting passes
- ✅ No security vulnerabilities introduced

#### 6.2 Address CI Failures
If CI fails:
1. Review error logs in GitHub Actions
2. Reproduce locally: `poetry run pytest tests/ -v`
3. Fix issues following the same TDD workflow
4. Commit and push fixes

## Best Practices

### DO ✅

1. **Write Tests First**
   - Always write failing tests before implementation
   - Tests should clearly document expected behavior

2. **Keep Tests Simple**
   - One assertion per test when possible
   - Use descriptive test names: `test_handle_empty_prefix_returns_empty_string`

3. **Test Edge Cases**
   - Empty values
   - None values
   - Boundary conditions
   - Error conditions

4. **Use Fixtures**
   ```python
   @pytest.fixture
   def sample_profile():
       return {
           "full_name": "John Doe",
           "job_title": "Engineer",
       }
   
   def test_profile_creation(sample_profile):
       profile = LinkedInProfile(**sample_profile)
       assert profile.full_name == "John Doe"
   ```

5. **Mock External Dependencies**
   ```python
   @patch('cqc_lem.utilities.linkedin.scrapper.requests.get')
   def test_fetch_profile(mock_get):
       mock_get.return_value.json.return_value = {"name": "Test"}
       # Test implementation
   ```

6. **Run Tests Frequently**
   - After every small change
   - Use test watchers for continuous feedback:
     ```bash
     poetry run pytest-watch tests/unit/
     ```

### DON'T ❌

1. **Don't Skip Writing Tests**
   - Never implement code without tests
   - Never commit untested code

2. **Don't Test Implementation Details**
   - Test behavior, not internal implementation
   - Avoid testing private methods directly

3. **Don't Ignore Failing Tests**
   - Fix or remove failing tests immediately
   - Never commit code with failing tests

4. **Don't Write Overly Complex Tests**
   - If test is complex, refactor the code being tested
   - Keep test logic simple and readable

5. **Don't Test Framework Code**
   - Don't test third-party libraries
   - Don't test Python built-ins
   - Focus on your application logic

## Coverage Goals by Module

| Module | Current | Minimum Target | Aspirational |
|--------|---------|----------------|--------------|
| scrapper.py | 10% | 70% | 85% |
| db.py | 20% | 70% | 85% |
| ai_helper.py | 21% | 70% | 85% |
| carousel_creator.py | 27% | 70% | 85% |
| profile.py | 62% | 70% | 85% |
| logger.py | 58% | 70% | 85% |

## Test Organization

```
tests/
├── unit/               # Fast, isolated tests with mocked dependencies
│   ├── utilities/
│   │   ├── linkedin/
│   │   │   ├── test_scrapper.py      # Scraper tests
│   │   │   └── test_poster.py        # Poster tests
│   │   ├── ai/
│   │   │   └── test_ai_helper.py     # AI helper tests
│   │   └── test_db.py                # Database tests
│   └── app/
├── integration/        # Tests with multiple components
└── e2e/               # End-to-end workflow tests
```

## Common Test Patterns

### Testing Database Operations
```python
def test_update_post_status(mock_database_connection):
    """Test updating post status in database."""
    # Arrange
    mock_cursor = mock_database_connection['cursor']
    
    # Act
    update_db_post_status(post_id=1, status='PUBLISHED')
    
    # Assert
    mock_cursor.execute.assert_called_once()
    assert 'UPDATE' in mock_cursor.execute.call_args[0][0]
```

### Testing API Integrations
```python
@patch('cqc_lem.utilities.ai.client.OpenAI')
def test_generate_ai_content(mock_openai):
    """Test AI content generation."""
    # Arrange
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Generated content"
    mock_openai.return_value.chat.completions.create.return_value = mock_response
    
    # Act
    result = generate_ai_response(prompt="Test prompt")
    
    # Assert
    assert result == "Generated content"
```

### Testing Error Handling
```python
def test_handle_connection_error():
    """Test proper handling of connection errors."""
    with pytest.raises(ConnectionError):
        scrape_profile(url="invalid://url")
```

## Troubleshooting

### Tests Pass Locally But Fail in CI
1. Check Python version matches CI environment (3.12)
2. Verify all dependencies are in poetry.lock
3. Check for environment-specific issues
4. Review CI logs for specific error messages

### Coverage Not Increasing
1. Review coverage report: `open htmlcov/index.html`
2. Identify uncovered lines (shown in red)
3. Add tests that execute those lines
4. Ensure tests actually run the code (not just mock it)

### Slow Tests
1. Mark slow tests: `@pytest.mark.slow`
2. Run fast tests frequently: `pytest -m "not slow"`
3. Use mocks instead of real services
4. Run targeted tests during development

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [TODO Project Timeline](./TODO_PROJECT_TIMELINE.md)
- [Test Suite Documentation](../tests/README.md)
- [Contributing Guidelines](../CONTRIBUTING.md)

## Questions?

If you have questions about the TDD workflow:
1. Check this documentation
2. Review existing tests for examples
3. Consult TODO_PROJECT_TIMELINE.md
4. Ask in pull request or issue comments
