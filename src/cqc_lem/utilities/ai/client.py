import os

from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("LITELLM_MASTER_KEY", os.getenv("OPENAI_API_KEY")),
    base_url=os.getenv("LITELLM_BASE_URL", "http://litellm:4000"),
)
