---
applyTo: "src/cqc_lem/utilities/ai/**"
---

# AI / LLM Instructions

These rules apply to all files under `src/cqc_lem/utilities/ai/`.

## Client

All LLM calls must use the shared client from `client.py`:

```python
from cqc_lem.utilities.ai.client import client
```

`client` is an OpenAI-compatible client that proxies to LiteLLM at `http://litellm:4000`. Changing `LITELLM_BASE_URL` in `.env` switches the target without any code changes.

## Model Aliases — Always Use These

| Alias | When to use |
|---|---|
| `lem-simple` | Short output ≤300 chars: refine message, summarize briefly, comma-separated list |
| `lem-medium` | Balanced: comments, post refinement, blog/web summaries, engagement prompts |
| `lem-complex` | Long-form: thought leadership, personal story, industry news, video scripts |
| `lem-image` | DALL-E 3 image generation (`client.images.generate`) |
| `lem-router` | Auto-route: use when the correct tier is ambiguous |

Never hardcode `gpt-4o-mini`, `gpt-4o`, `claude-*`, or any specific model name.

## Token Usage Tracking

After every `client.chat.completions.create()` call, track usage:

```python
from cqc_lem.utilities.observability import track_llm_call
import time

start = time.time()
response = client.chat.completions.create(model="lem-medium", messages=[...])
track_llm_call(
    model="lem-medium",
    prompt_tokens=response.usage.prompt_tokens,
    completion_tokens=response.usage.completion_tokens,
    latency_ms=int((time.time() - start) * 1000),
)
```

## Response Extraction

```python
content = response.choices[0].message.content
if content is None:
    return None  # never crash on empty response
```

## Error Handling

Wrap API calls in try/except for `openai.RateLimitError` and `openai.APIError`. Log errors with `myprint()`, never `print()`.

## No Direct OpenAI Import

Never import from `openai` directly in `ai_helper.py`. The client handles the underlying SDK.
