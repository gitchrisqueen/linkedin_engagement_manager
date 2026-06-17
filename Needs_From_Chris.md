# Things Needed From Chris

Items I need from you to proceed. Mark each `(complete)` when done and I'll continue any tasks that were blocked.

---

## GitHub Repository Secrets

These go in **GitHub → Settings → Secrets and variables → Actions → Repository secrets** (`https://github.com/gitchrisqueen/linkedin_engagement_manager/settings/secrets/actions`).

- [ ] **`GITGUARDIAN_API_KEY`** — Required by `.github/workflows/gitguardian-scan.yml`. Get it from your GitGuardian dashboard at `https://dashboard.gitguardian.com/api/personal-access-tokens`. Create a token with "Incident" scope.

- [ ] **`CODECOV_TOKEN`** — Required by all three test workflows for coverage upload. Get it from `https://app.codecov.io/gh/gitchrisqueen/linkedin_engagement_manager` after linking the repo (free for public repos, or connect via GitHub login).

- [ ] **`ANTHROPIC_API_KEY`** — Required by LiteLLM to route `lem-complex` requests to Claude. Get from `https://console.anthropic.com/settings/keys`.

- [ ] **`OPENROUTER_API_KEY`** — Required by LiteLLM for `lem-medium` fallback routing. Get from `https://openrouter.ai/settings/keys`.

- [ ] **`LITELLM_MASTER_KEY`** — A secret string you choose yourself (like a password) used to authenticate requests from the app to the LiteLLM proxy. Example: `sk-lem-localdev-abc123`. Set this same value in your `.env` file as `LITELLM_MASTER_KEY=<your-value>`.

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

- [ ] **`POSTHOG_API_KEY`** — Sign up at `https://us.posthog.com/signup` (free tier is generous). After signup, go to **Project Settings → Project API Key**. Copy the key and add it to your `.env` as shown above, and as a GitHub secret named `POSTHOG_API_KEY`.

---

## Ollama (Optional — Local Model Fallback)

Ollama runs locally inside Docker. No API key needed, but the first run will download model weights (~2 GB for llama3.2:3b). This happens automatically when the container starts. No action needed unless you want to pre-pull a specific model.

---

## Notes

- All secrets must be set in GitHub before CI workflows can pass (GitGuardian scan will fail without `GITGUARDIAN_API_KEY`; coverage upload will warn without `CODECOV_TOKEN`).
- The `.env` changes are needed before running `docker compose up` locally with LiteLLM.
- Existing secrets (`OPENAI_API_KEY`, `AWS_*`, etc.) are unchanged.
