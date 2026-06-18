# Things Needed From Chris

Items I need from you to proceed. Mark each `(complete)` when done and I'll continue any tasks that were blocked.

---

## GitHub Repository Secrets

These go in **GitHub → Settings → Secrets and variables → Actions → Repository secrets** (`https://github.com/gitchrisqueen/linkedin_engagement_manager/settings/secrets/actions`).

- [x] **`GITGUARDIAN_API_KEY`** — Required by `.github/workflows/gitguardian-scan.yml`. _(complete)_

- [x] **`CODECOV_TOKEN`** — Required by all three test workflows for coverage upload. _(complete)_

- [ ] **`ANTHROPIC_API_KEY`** — Required by LiteLLM to route `lem-complex` requests to Claude. Get from `https://console.anthropic.com/settings/keys`. _(adding later)_

- [x] **`OPENROUTER_API_KEY`** — Required by LiteLLM for `lem-medium` fallback routing. _(complete)_

- [x] **`LITELLM_MASTER_KEY`** — Master key for LiteLLM proxy authentication. _(complete)_

---

## Local `.env` File Additions

Add these to your `.env` file in the project root (alongside existing `OPENAI_API_KEY` etc.):

```
# LiteLLM proxy
LITELLM_BASE_URL=http://litellm:4000
LITELLM_MASTER_KEY=<same value as GitHub secret above>

# Claude / Anthropic
ANTHROPIC_API_KEY=<your key from console.anthropic.com>

# OpenRouter
OPENROUTER_API_KEY=<your key from openrouter.ai>

# PostHog observability
POSTHOG_API_KEY=<your key — see below>
POSTHOG_HOST=https://us.i.posthog.com
```

---

## PostHog Account

- [x] **`POSTHOG_API_KEY`** — _(complete)_

---

## Ollama (Optional — Local Model Fallback)

Ollama runs locally inside Docker. No API key needed, but the first run will download model weights (~2 GB for llama3.2:3b). This happens automatically when the container starts. No action needed unless you want to pre-pull a specific model.

---

## Deferred M5 Issues (Answered)

**#26 — DM automation deduplication** (`run_automation.py`):
Never send the same message twice. Need a follow-up message template system with `days_since_last_message` and `message_follow_up_index` to track which message in a sequence was sent. AI should use the template but customize it per individual — smart follow-up to progress conversations without being spammy or annoying. _Implementing in M5._

**#27 — Profile scraping: awards & interests** (`scrapper.py`):
Need a live E2E test against a real account. Can use Christopher's LinkedIn profile: https://www.linkedin.com/in/christopherqueen/. _Stub code first, then E2E test against live account._

**#30 — Geolocation from database** (`selenium_util.py`):
Migration can run once all prior dependent code is merged to main first. _Will create Flyway migration and implement after M1–M4 merge._

---

## Notes

- All secrets must be set in GitHub before CI workflows can pass (GitGuardian scan will fail without `GITGUARDIAN_API_KEY`; coverage upload will warn without `CODECOV_TOKEN`).
- The `.env` changes are needed before running `docker compose up` locally with LiteLLM.
- Existing secrets (`OPENAI_API_KEY`, `AWS_*`, etc.) are unchanged.
- `ANTHROPIC_API_KEY` is the only remaining item — add it when ready and the `lem-complex` LLM tier will activate.
