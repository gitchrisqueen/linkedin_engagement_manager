import base64
import re
from typing import Optional

import replicate
from replicate.exceptions import ReplicateError

from cqc_lem.utilities.env_constants import REPLICATE_USERNAME
from cqc_lem.utilities.logger import log_info, log_error, log_warning

TRAINER_MODEL = "replicate/fast-flux-trainer"

# Hardware SKU for the destination model (inference, not training).
# Training hardware is determined by the trainer itself.
_DESTINATION_HARDWARE = "gpu-a40-large"


def _sanitize_model_name(trigger_word: str, user_id: int) -> str:
    slug = re.sub(r"[^a-z0-9-]", "-", trigger_word.lower()).strip("-")
    return f"{slug}-avatar-{user_id}"


def _ensure_destination_model(owner: str, name: str) -> None:
    """Create the destination model on Replicate if it doesn't already exist.

    Replicate requires the destination model to exist before a training can
    push weights to it. A 409 (conflict) means it already exists — that's fine.
    """
    try:
        replicate.models.get(f"{owner}/{name}")
    except ReplicateError as get_err:
        if get_err.status != 404:
            raise
        try:
            replicate.models.create(
                owner=owner,
                name=name,
                visibility="private",
                hardware=_DESTINATION_HARDWARE,
            )
            log_info("Created destination model on Replicate", action_type="avatar_model_create")
        except ReplicateError as create_err:
            if create_err.status != 409:  # 409 = race-created between get and create
                raise


def start_avatar_training(user_id: int, zip_bytes: bytes, trigger_word: str) -> str:
    """Upload ZIP of training photos and start a FLUX.1 LoRA fine-tune on Replicate.

    Returns the Replicate training ID. Raises on failure so the caller can surface
    the error and skip the credit deduction.
    """
    if not REPLICATE_USERNAME:
        raise ValueError("REPLICATE_USERNAME must be set to create a training destination")

    model_name = _sanitize_model_name(trigger_word, user_id)
    destination = f"{REPLICATE_USERNAME}/{model_name}"

    # Replicate requires the destination model to pre-exist.
    _ensure_destination_model(REPLICATE_USERNAME, model_name)

    # Resolve the trainer's latest version — do not hardcode a version hash.
    trainer = replicate.models.get(TRAINER_MODEL)
    if not trainer.latest_version:
        raise RuntimeError(f"Could not resolve latest version of {TRAINER_MODEL}")
    trainer_version = trainer.latest_version

    zip_b64 = base64.b64encode(zip_bytes).decode("utf-8")
    zip_data_uri = f"data:application/zip;base64,{zip_b64}"

    log_info(
        "Starting avatar training",
        user_id=user_id,
        action_type="avatar_training_start",
    )

    training = replicate.trainings.create(
        model=TRAINER_MODEL,
        version=trainer_version,
        input={
            "input_images": zip_data_uri,
            "trigger_word": trigger_word,
            "steps": 1000,
        },
        destination=destination,
    )

    log_info(
        "Avatar training started",
        user_id=user_id,
        task_name="avatar_training",
    )
    return training.id


def poll_training_status(training_id: str) -> tuple[str, Optional[str]]:
    """Fetch current status from Replicate. Returns (status, model_ref).

    model_ref is only populated when status == 'succeeded'.
    """
    try:
        training = replicate.trainings.get(training_id)
        status = training.status or "processing"

        status_map = {
            "starting": "starting",
            "processing": "processing",
            "succeeded": "succeeded",
            "failed": "failed",
            "canceled": "canceled",
        }
        mapped_status = status_map.get(status, "processing")

        model_ref: Optional[str] = None
        if mapped_status == "succeeded" and training.output:
            model_ref = training.output.get("version") or str(training.output)

        return mapped_status, model_ref
    except Exception as exc:
        log_error("Failed to poll avatar training status", exc=exc, task_name="poll_training")
        return "processing", None


def generate_image_with_avatar(prompt: str, model_ref: str) -> str:
    """Run inference on a trained avatar LoRA model. Returns a local file path.

    Delegates to the existing get_flux_image_via_replicate utility so all
    file-saving logic stays in one place.
    """
    from cqc_lem.utilities.ai.ai_helper import get_flux_image_via_replicate
    try:
        return get_flux_image_via_replicate(prompt, ref=model_ref)
    except Exception as exc:
        log_warning(
            "Avatar inference failed, falling back to base Flux model",
            exc=exc,
            action_type="avatar_inference_fallback",
        )
        from cqc_lem.utilities.ai.ai_helper import generate_flux1_image_from_prompt
        return generate_flux1_image_from_prompt(prompt)
