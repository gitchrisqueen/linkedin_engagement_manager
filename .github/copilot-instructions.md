# LinkedIn Engagement Manager — GitHub Copilot Instructions

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
├── ui/            React SPA (src/, dist/ is built output served by FastAPI)
└── aws/           AWS CDK stacks
tests/
├── unit/          Fast tests — mock all I/O
├── integration/   Require MySQL + Redis service containers
└── e2e/           Require selenium/standalone-chrome
.litellm/
├── config.yaml    LiteLLM model aliases and routing config
└── complexity_router.py  Pre-call hook: routes lem-router by prompt complexity
```

## Code Conventions

- **Logging:** Never use `print()`. Use `myprint()` from `cqc_lem.utilities.logger`.
- **Type hints:** Required on all function signatures.
- **Enums:** Use `PostStatus`, `PostType`, `LogActionType` from `db.py` — never raw strings.
- **Imports:** Absolute from `cqc_lem.*` throughout.
- **Database:** All DB access through functions in `utilities/db.py`. No raw SQL in other modules.
- **Secrets:** Never hardcode. Use `.env` with `load_dotenv()`. See `.env.example` for required vars.
- **No `print()`:** Always `myprint()`.
- **Comments:** Only add when WHY is non-obvious.

## Files Copilot Must Never Modify

- `.env` — live credentials
- `poetry.lock` — lockfile managed by Poetry
- `src/cqc_lem/ui/dist/` — built frontend artifacts (auto-generated)
- `aws/cdk.out/` — CDK synth output (auto-generated)

## AI Call Pattern

All LLM calls go through LiteLLM proxy via `utilities/ai/client.py`:

```python
from cqc_lem.utilities.ai.client import client
response = client.chat.completions.create(model="lem-simple", messages=[...])
```

**Model tier aliases:**

| Alias | Use case |
|---|---|
| `lem-simple` | Short outputs ≤300 chars, refine/summarize/list |
| `lem-medium` | Balanced: comments, refinements, summaries |
| `lem-complex` | Long-form: thought leadership, personal story, news |
| `lem-image` | Image generation (DALL-E 3) |
| `lem-router` | Auto-routes by prompt complexity |

## Selenium Pattern

Always use `get_docker_driver()` from `selenium_util.py`. Connect to `selenium-chrome:4444`. Never instantiate `webdriver.Chrome()` directly. Use `click_element_wait_retry()` for all clicks.

## Testing Standards

- ≥80% patch coverage enforced via Codecov.
- Unit tests in `tests/unit/` — mock all external I/O.
  - `mock_openai_client` fixture — patches `cqc_lem.utilities.ai.client.OpenAI`
  - `mock_database_connection` fixture — patches `mysql.connector.connect`
  - `mock_selenium_driver` fixture — patches `selenium.webdriver.Chrome`
- Integration tests in `tests/integration/` — use real MySQL + Redis.
- E2E tests in `tests/e2e/` — use real standalone-chrome container.
- Run: `poetry run pytest tests/unit -v --tb=short`
- Run with coverage: `poetry run pytest --cov=src/cqc_lem --cov-report=xml`

## CI/CD

Required status checks before merge:
- `CI / Unit Tests`
- `CI / Integration Test w/ Coverage`
- `CodeQL Security Analysis`
- `GitGuardian Security Scan`

Dependabot creates PRs for pip, github-actions, docker, and npm weekly. Dependabot PRs with failing CI are auto-tagged — high priority to fix.

## Observability

```python
from cqc_lem.utilities.observability import track_llm_call, track_task, track_api_call
```

PostHog receives LLM usage (model, tokens, latency, estimated cost) and Celery task metrics. No Prometheus or Jaeger — those services were removed.
