# LinkedIn Engagement Manager — Claude Code Context

## Project Overview

LinkedIn Engagement Manager (LEM) automates LinkedIn engagement: Selenium-based scraping, AI-generated content (via LiteLLM proxy routing to OpenAI / Claude / Ollama / OpenRouter), Celery task queue, React SPA frontend, MySQL persistence, and FastAPI backend.

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| Web framework | FastAPI |
| Task queue | Celery + Redis |
| Database | MySQL 8 |
| Browser automation | Selenium 4 + `selenium/standalone-chrome` |
| AI proxy | LiteLLM (port 4000) |
| Frontend | React 18 + Vite + TailwindCSS |
| Package manager | Poetry |
| Infra | Docker Compose (local), AWS CDK (cloud) |
| Observability | PostHog |

## Directory Map

```
src/cqc_lem/
├── api/           FastAPI app (main.py, routers)
├── app/           Celery tasks (run_scheduler.py, run_automation.py, my_celery.py)
├── utilities/
│   ├── ai/        LiteLLM-backed AI helpers (ai_helper.py, client.py)
│   ├── linkedin/  Selenium automation (scrapper.py, poster.py, commenter.py)
│   ├── db.py      All database access (no raw SQL outside this file)
│   ├── logger.py  myprint() — use this instead of print()
│   └── selenium_util.py  get_docker_driver() — always use this for WebDriver
├── ui/            React SPA (src/, dist/ is built output)
└── aws/           AWS CDK stacks
tests/
├── unit/          Fast tests — mock all I/O
├── integration/   Require MySQL + Redis service containers
└── e2e/           Require selenium/standalone-chrome
.litellm/
├── config.yaml    LiteLLM model aliases and routing config
└── complexity_router.py  Pre-call hook for lem-router model
```

## Code Conventions

- **Logging:** Never use `print()`. Use `myprint()` from `cqc_lem.utilities.logger`.
- **Type hints:** Required on all function signatures.
- **Enums:** Use `PostStatus`, `PostType`, `LogActionType` from `db.py` for status fields — never raw strings.
- **Imports:** Absolute imports from `cqc_lem.*` throughout.
- **Database:** All DB access goes through functions in `utilities/db.py`. No raw SQL in other modules.
- **Secrets:** Never hardcode. Use `.env` with `load_dotenv()`. See `.env.example` for required variables.
- **Comments:** Only add a comment when the WHY is non-obvious. No docstring blocks.

## AI Call Pattern

All LLM calls go through LiteLLM proxy via `utilities/ai/client.py`:

```python
from cqc_lem.utilities.ai.client import client
response = client.chat.completions.create(model="lem-simple", messages=[...])
```

**Model tier aliases** (defined in `.litellm/config.yaml`):

| Alias | Use case |
|---|---|
| `lem-simple` | Short outputs ≤300 chars: refine, summarize briefly, comma list |
| `lem-medium` | Balanced: comments, post refinement, blog summaries |
| `lem-complex` | Long-form: thought leadership, personal story, industry news |
| `lem-image` | Image generation (DALL-E 3) |
| `lem-router` | Auto-routes by prompt complexity via `LEMComplexityRouter` |

See `ai_helper.py` for the per-function model assignment.

## Selenium Pattern

Always use `get_docker_driver()` from `selenium_util.py`. It connects to `selenium-chrome:4444`, polls readiness, and sets 1920×1080. Never instantiate `webdriver.Chrome()` directly.

Use `click_element_wait_retry()` for all click interactions — it handles transient DOM timing issues.

## Testing Standards

- All new/modified code: ≥80% patch coverage enforced by Codecov.
- **Unit tests** (`tests/unit/`): mock all external I/O.
  - Mock OpenAI: `mock_openai_client` fixture (patches `cqc_lem.utilities.ai.client.OpenAI`)
  - Mock DB: `mock_database_connection` fixture (patches `mysql.connector.connect`)
  - Mock Selenium: `mock_selenium_driver` fixture
- **Integration tests** (`tests/integration/`): use real MySQL + Redis service containers.
- **E2E tests** (`tests/e2e/`): use real `selenium/standalone-chrome` container.
- Run unit tests: `poetry run pytest tests/unit -v --tb=short`
- Run with coverage: `poetry run pytest --cov=src/cqc_lem --cov-report=xml`

## Observability

Track events via `utilities/observability.py`:

```python
from cqc_lem.utilities.observability import track_llm_call, track_task, track_api_call
```

PostHog receives LLM usage (model, tokens, latency, cost) and Celery task metrics for fine-tuning decisions.

## CI Gates

Before merging any PR, all of the following must pass:
- `CI / Unit Tests`
- `CI / Integration Test w/ Coverage`
- `CodeQL Security Analysis`
- `GitGuardian Security Scan`

## Known Gotchas

- `get_docker_driver()` previously connected to Selenium Grid hub+node. It now connects to `selenium/standalone-chrome:latest` at port 4444.
- `ai_helper.py` had all functions hardcoded to `model="gpt-4o-mini"` — they now use tier aliases.
- `run_scheduler.py:22` previously had a `raise ValueError("This is a test error")` — this was removed in M3.
- PostHog replaces Prometheus + Jaeger (both removed from docker-compose).
- `linkedin-preview` service (external) was removed — preview is now the native `LinkedInPostPreview.tsx` component.
