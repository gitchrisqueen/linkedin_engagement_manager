# LinkedIn Engagement Manager (LEM)

## Overview

LinkedIn Engagement Manager (LEM) is an automated solution for managing engagement and post interactions on LinkedIn. This tool allows users to automate the process of commenting, sending direct messages (DMs), responding to comments, and scheduling posts. All content (text, carousels, videos) is AI-generated and passes through sentiment analysis for appropriateness. LEM also includes a preview and approval system, enabling manual or automated approval of content.

## Key Features
- **Automated Engagement**: Commenting, messaging profile viewers, and replying to post comments with scheduled engagement tasks.
- **AI-Generated Content**: Modular AI services generate carousel, text, and video content.
- **Sentiment Analysis**: Ensures content is appropriate, aligned with user preferences.
- **Approval Workflow**: Preview and approve content before publishing or allow for automatic approval.
- **Video Creation**: Generate videos from prompts using AI.
- **Summarizing Recent Activity**: Summarize recent LinkedIn activities and craft personalized responses.
- **Date-Time Picker for Scheduled Posts**: Edit scheduled posts with a date-time picker for easy scheduling.
- **Dockerized Environment**: Easily deployable to the cloud using Docker containers.
- **Modular Design**: Content generation modules can be swapped out for any SaaS services.
- **User Dashboard**: Mobile and web-friendly dashboard for monitoring and controlling the engagement process.

## Tech Stack
- **Python** with **Selenium** for automation tasks.
- **MySQL** as the relational database.
- **Docker** to containerize the application for local development and cloud deployment.
- **AI Services**: Integrated AI models to generate content and perform sentiment analysis.
- **Streamlit** for the user interface.

## Getting Started

### Prerequisites
1. **Docker** installed on your system.
2. **Python 3.9+** for local development.
3. **MySQL 8.0** or above (can be run inside Docker).
4. **Streamlit** for running the user interface.
5. Necessary API keys for AI services (e.g., OpenAI API key).

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/linkedin-engagement-manager.git
   cd linkedin-engagement-manager
   ```

2. Set up the environment:
   ```bash
   cp .env.example .env
   # Fill in necessary API keys, MySQL credentials, etc.
   ```

3. (Optional) Install ngrok via Homebrew with the following command:
   ```bash
   brew install ngrok/ngrok/ngrok
   ```

4. Build and run the Docker containers via shell scriopt:
   ```bash
   ./run.sh
   ```

4. Access the web dashboard:
   Open the urls printed in the console in your browser.

## Testing

This project uses pytest for testing with comprehensive unit, integration, and end-to-end tests.

### Running Tests

1. **Install test dependencies:**
   ```bash
   poetry install --with test
   ```

2. **Run all tests:**
   ```bash
   poetry run pytest
   ```

3. **Run tests with coverage:**
   ```bash
   poetry run pytest --cov=src/cqc_lem --cov-report=html --cov-report=term
   ```

4. **Run specific test categories:**
   ```bash
   # Run only unit tests
   poetry run pytest tests/unit -v
   
   # Run only integration tests
   poetry run pytest tests/integration -v
   
   # Run tests by marker
   poetry run pytest -m "unit" -v
   poetry run pytest -m "not slow" -v
   ```

5. **Run specific test file:**
   ```bash
   poetry run pytest tests/unit/utilities/test_db.py -v
   ```

6. **Run tests matching a pattern:**
   ```bash
   poetry run pytest -k "test_database" -v
   ```

7. **Run tests with detailed output:**
   ```bash
   poetry run pytest -v --tb=short
   ```

### Test Markers

Tests are organized with the following markers:
- `unit` - Fast unit tests with mocked dependencies
- `integration` - Integration tests requiring multiple components
- `e2e` - End-to-end tests
- `slow` - Tests that take longer to execute
- `requires_openai` - Tests requiring OpenAI API access
- `requires_database` - Tests requiring database connection
- `requires_selenium` - Tests requiring browser automation

### Test Coverage Goals

- **Minimum Coverage**: 70% of core modules
- **Target Coverage**: 85%+ of core modules
- **CI/CD**: Automated test execution on all pull requests

### Continuous Integration

Tests are automatically run on:
- Every push to `main`, `develop`, or `copilot/**` branches
- All pull requests to `main` or `develop` branches

View test results in the GitHub Actions tab of the repository.

### Contributing
We welcome contributions to the project. Please submit a pull request with clear documentation of any changes.

## License
MIT License.
