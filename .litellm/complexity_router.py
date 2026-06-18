"""LiteLLM pre-call hook: routes 'lem-router' requests to tier based on prompt complexity."""
from litellm.integrations.custom_logger import CustomLogger

SIMPLE_SIGNALS = ["refine", "shorten", "summarize briefly", "comma separated", "short list"]
COMPLEX_SIGNALS = [
    "thought leadership", "viral post", "personal story", "industry news",
    "buyer stage", "comprehensive", "step-by-step", "framework",
]


class LEMComplexityRouter(CustomLogger):
    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        if data.get("model") != "lem-router":
            return data
        prompt = " ".join(
            m.get("content", "") for m in data.get("messages", [])
            if isinstance(m.get("content"), str)
        ).lower()
        score = (
            sum(1 for s in COMPLEX_SIGNALS if s in prompt)
            - sum(1 for s in SIMPLE_SIGNALS if s in prompt)
        )
        token_estimate = len(prompt.split())
        if score >= 2 or token_estimate > 800:
            data["model"] = "lem-complex"
        elif score >= 1 or token_estimate > 300:
            data["model"] = "lem-medium"
        else:
            data["model"] = "lem-simple"
        return data


proxy_handler_instance = LEMComplexityRouter()
