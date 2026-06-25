"""RunwayML video-model abstraction.

Isolates the RunwayML SDK shape so model migration lives in one place. gen3a_turbo
(the previous default) is deliberately absent — Runway sunsets it on 2026-07-30.
gen4_turbo is the drop-in successor; gen4.5 and veo3.1 are opt-in higher tiers
reachable through the same SDK client.
"""
import base64
import time
from dataclasses import dataclass
from typing import Optional

from runwayml import RunwayML

from cqc_lem.utilities.env_constants import DEFAULT_VIDEO_MODEL, DEFAULT_VIDEO_RATIO
from cqc_lem.utilities.logger import log_debug, log_warning


@dataclass(frozen=True)
class VideoModelSpec:
    sdk_model: str           # value passed to the SDK 'model' kwarg
    endpoint: str            # RunwayML client attribute, e.g. 'image_to_video'
    cost_per_second: float   # USD, for cost estimates
    supports_prompt_image: bool
    default_ratio: str


# Runway API models reachable through the same RunwayML() client.
VIDEO_MODELS: dict[str, VideoModelSpec] = {
    "gen4_turbo": VideoModelSpec("gen4_turbo", "image_to_video", 0.05, True, "960:960"),
    "gen4.5":     VideoModelSpec("gen4.5",     "image_to_video", 0.12, True, "960:960"),
    "veo3.1":     VideoModelSpec("veo3.1",     "image_to_video", 0.30, True, "1280:720"),
}

DEFAULT_VIDEO_DURATION = 5

# Friendly aspect-ratio aliases -> Runway resolution strings.
RATIO_ALIASES = {
    "1:1": "960:960",
    "16:9": "1280:720",
    "9:16": "720:1280",
    "4:5": "864:1080",
    "5:4": "1080:864",
    "4:3": "1104:832",
    "3:4": "832:1104",
}

_POLL_SECONDS = 10


def resolve_ratio(ratio: str) -> str:
    return RATIO_ALIASES.get(ratio, ratio)


def estimate_video_cost(model: str, duration: int = DEFAULT_VIDEO_DURATION) -> float:
    spec = VIDEO_MODELS.get(model)
    return round(spec.cost_per_second * duration, 3) if spec else 0.0


def _to_prompt_image(image_path_or_url: str) -> str:
    """Hosted URLs pass through; local files become a base64 PNG data URI."""
    if image_path_or_url.startswith(("http://", "https://")):
        return image_path_or_url
    with open(image_path_or_url, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def _create_task(endpoint, create_kwargs: dict):
    """Call endpoint.create, retrying without optional kwargs if the pinned SDK
    version rejects them (resilience across runwayml >=2.1,<5.0)."""
    try:
        return endpoint.create(**create_kwargs)
    except TypeError:
        keep = ("model", "prompt_image", "prompt_text", "ratio")
        return endpoint.create(**{k: v for k, v in create_kwargs.items() if k in keep})


def create_runway_video(
    image_path_or_url: str,
    prompt: str,
    *,
    model: str = DEFAULT_VIDEO_MODEL,
    ratio: str = DEFAULT_VIDEO_RATIO,
    duration: int = DEFAULT_VIDEO_DURATION,
    seed: Optional[int] = None,
) -> Optional[str]:
    """Create a video from an image via the RunwayML API and return its URL.

    Backwards compatible with the old positional ``(image_path, prompt)`` call.
    Raises on creation failure so callers' Pexels fallback can trigger; returns
    None only when the task itself reports FAILED / produces no output.
    """
    spec = VIDEO_MODELS.get(model)
    if spec is None:
        raise ValueError(f"Unknown video model {model!r}. Known: {sorted(VIDEO_MODELS)}")

    runway_client = RunwayML()
    resolved_ratio = resolve_ratio(ratio)
    create_kwargs = {
        "model": spec.sdk_model,
        "prompt_image": _to_prompt_image(image_path_or_url),
        "prompt_text": prompt,
        "ratio": resolved_ratio,
        "duration": duration,
    }
    if seed is not None:
        create_kwargs["seed"] = seed

    endpoint = getattr(runway_client, spec.endpoint)
    log_debug(
        f"Runway create model={spec.sdk_model} ratio={resolved_ratio} duration={duration}s",
        ai_model=spec.sdk_model,
    )
    try:
        task = _create_task(endpoint, create_kwargs)
    except Exception as e:
        log_warning("Runway video creation failed", exc=e, ai_model=spec.sdk_model)
        raise

    task_id = task.id
    time.sleep(_POLL_SECONDS)
    task = runway_client.tasks.retrieve(task_id)
    while task.status not in ("SUCCEEDED", "FAILED"):
        time.sleep(_POLL_SECONDS)
        task = runway_client.tasks.retrieve(task_id)

    if task.status == "SUCCEEDED" and getattr(task, "output", None):
        return task.output[0]
    log_warning(f"Runway task {task_id} ended status={task.status}", ai_model=spec.sdk_model)
    return None
