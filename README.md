# LinkedIn Engagement Manager (LEM)

## Overview

LinkedIn Engagement Manager (LEM) is an automated solution for managing engagement and post interactions on LinkedIn. This tool automates commenting, sending direct messages (DMs), responding to comments, and scheduling posts. All content (text, carousels, videos) is AI-generated via a LiteLLM proxy and passes through sentiment analysis for appropriateness. LEM includes a preview and approval system enabling manual or automated content approval before publishing.

## Key Features
- **Automated Engagement**: Commenting, messaging profile viewers, and replying to post comments with scheduled engagement tasks.
- **AI-Generated Content**: LiteLLM-proxied AI services generate carousel, text, and video content with tiered model routing (`lem-simple`, `lem-medium`, `lem-complex`).
- **Sentiment Analysis**: Ensures content is appropriate and aligned with user preferences.
- **Approval Workflow**: Preview and approve content before publishing or allow automatic approval.
- **Video Creation**: Generate videos from prompts using AI.
- **Summarizing Recent Activity**: Summarize recent LinkedIn activities and craft personalized responses.
- **Date-Time Picker for Scheduled Posts**: Edit scheduled posts with a date-time picker for easy scheduling.
- **Dockerized Environment**: Easily deployable locally or to the cloud using Docker Compose.
- **Modular Design**: Content generation modules can be swapped out for any SaaS services via LiteLLM aliases.
- **React SPA Dashboard**: Mobile and web-friendly React dashboard for monitoring and controlling the engagement process.
- **Observability**: PostHog-based LLM usage tracking, Celery task metrics, and API latency monitoring.

## Tech Stack
- **Python 3.12+** with **FastAPI** for the backend API.
- **React 18 + Vite + TailwindCSS** for the single-page frontend.
- **Selenium 4** (`selenium/standalone-chrome`) for LinkedIn browser automation.
- **Celery + Redis** for distributed task scheduling and execution.
- **MySQL 8** as the relational database.
- **LiteLLM** (port 4000) as an AI proxy routing to OpenAI, Anthropic, Ollama, and OpenRouter.
- **Docker Compose** for local orchestration; **AWS CDK** for cloud deployment.
- **PostHog** for observability (LLM cost, task metrics, API latency).
- **Poetry** for Python dependency management.

## Getting Started

### Prerequisites
1. **Docker** installed on your system.
2. **Python 3.12+** for local development (managed via Poetry).
3. **Poetry** for Python package management (`pip install poetry`).
4. **Node.js 18+** for frontend development (only needed if editing the React UI).
5. API keys for AI services (OpenAI, Anthropic, and/or OpenRouter — at least one required).
6. (Optional) **ngrok** for exposing local services publicly:
   ```bash
   brew install ngrok/ngrok/ngrok
   ```

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/gitchrisqueen/linkedin-engagement-manager.git
   cd linkedin-engagement-manager
   ```

2. Set up the environment:
   ```bash
   cp .env.example .env
   # Fill in required values: MySQL credentials, LinkedIn credentials,
   # AI API keys, LiteLLM master key, Docker image name, etc.
   ```

3. (Optional) Configure ngrok by setting `NGROK_AUTH_TOKEN`, `NGROK_CUSTOM_DOMAIN`,
   `NGROK_EDGE_TOKEN`, and the `NGROK_*_PREFIX` variables in your `.env` file.

4. Build and run the Docker containers:
   ```bash
   ./run.sh
   ```
   The script will prompt whether to build and push the Docker image, then start all
   services and print a table of local (or ngrok) URLs.

5. Access the services at the URLs printed in the console.

### Docker Image

The main application image (`${DOCKER_IMAGE_NAME}:latest`) is shared by the `web_app`,
`api`, `celery_worker`, `celery_beat`, and `flower` services. The `run.sh` script
handles building and optionally pushing this image to Docker Hub.

### AI Proxy (LiteLLM)

All LLM calls are routed through the LiteLLM proxy at `http://litellm:4000`. Model tier
aliases are defined in `.litellm/config.yaml`:

| Alias | Use case |
|---|---|
| `lem-simple` | Short outputs ≤300 chars |
| `lem-medium` | Balanced: comments, post refinement |
| `lem-complex` | Long-form: thought leadership, personal story |
| `lem-image` | Image generation (DALL-E 3) |
| `lem-router` | Auto-routes by prompt complexity |

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
   poetry run pytest tests/unit -v --tb=short

   # Run only integration tests (requires MySQL + Redis)
   poetry run pytest tests/integration -v

   # Run end-to-end tests (requires selenium/standalone-chrome)
   poetry run pytest tests/e2e -v
   ```

5. **Run specific test file:**
   ```bash
   poetry run pytest tests/unit/utilities/test_db.py -v
   ```

6. **Run tests matching a pattern:**
   ```bash
   poetry run pytest -k "test_database" -v
   ```

### Test Markers

Tests are organized with the following markers:
- `unit` — Fast tests with all external I/O mocked
- `integration` — Require real MySQL + Redis service containers
- `e2e` — Require `selenium/standalone-chrome` container
- `slow` — Tests that take longer to execute
- `requires_openai` — Tests requiring OpenAI API access
- `requires_database` — Tests requiring a database connection
- `requires_selenium` — Tests requiring browser automation

### Test Coverage Requirements

- **Minimum Coverage**: 80% of changed code (enforced by Codecov on every PR)
- **Target Coverage**: 85%+ of core modules
- **CI/CD**: Automated test execution on all pull requests

### Continuous Integration

All of the following CI gates must pass before merging any PR:
- `CI / Unit Tests`
- `CI / Integration Test w/ Coverage`
- `CodeQL Security Analysis`
- `GitGuardian Security Scan`

Tests run automatically on:
- Every push to `main` or `develop` branches
- All pull requests targeting `main` or `develop`

View test results in the GitHub Actions tab of the repository.

## Contributing
We welcome contributions to the project. Please submit a pull request with clear documentation of any changes. All CI gates must pass before review.

## License
MIT License.
