"""Unit tests for the RunwayML video-model abstraction."""

import pytest
from unittest.mock import patch

pytestmark = pytest.mark.unit


class TestEstimateAndResolve:
    def test_estimate_cost(self):
        from cqc_lem.utilities.ai.video_models import estimate_video_cost
        assert estimate_video_cost("gen4_turbo", 5) == 0.25
        assert estimate_video_cost("gen4.5", 5) == 0.60
        assert estimate_video_cost("unknown-model", 5) == 0.0

    def test_resolve_ratio_alias_and_passthrough(self):
        from cqc_lem.utilities.ai.video_models import resolve_ratio
        assert resolve_ratio("1:1") == "960:960"
        assert resolve_ratio("960:960") == "960:960"  # already a resolution

    def test_to_prompt_image_url_passthrough(self):
        from cqc_lem.utilities.ai.video_models import _to_prompt_image
        assert _to_prompt_image("https://x/y.png") == "https://x/y.png"

    def test_to_prompt_image_base64_for_local_file(self, tmp_path):
        from cqc_lem.utilities.ai.video_models import _to_prompt_image
        f = tmp_path / "img.png"
        f.write_bytes(b"\x89PNG\r\n")
        out = _to_prompt_image(str(f))
        assert out.startswith("data:image/png;base64,")


class TestCreateRunwayVideo:
    def test_passes_ratio_duration_seed_and_returns_url(self, mock_runwayml):
        from cqc_lem.utilities.ai.video_models import create_runway_video
        url = create_runway_video("https://img/base.png", "slow push-in",
                                  model="gen4_turbo", ratio="1:1", duration=5, seed=7)
        assert url == "https://runway.example/video.mp4"
        kwargs = mock_runwayml["client"].image_to_video.create.call_args[1]
        assert kwargs["model"] == "gen4_turbo"
        assert kwargs["prompt_image"] == "https://img/base.png"
        assert kwargs["ratio"] == "960:960"  # resolved from 1:1
        assert kwargs["duration"] == 5
        assert kwargs["seed"] == 7

    def test_omits_seed_when_none(self, mock_runwayml):
        from cqc_lem.utilities.ai.video_models import create_runway_video
        create_runway_video("https://img/base.png", "pan", model="gen4_turbo")
        kwargs = mock_runwayml["client"].image_to_video.create.call_args[1]
        assert "seed" not in kwargs

    def test_failed_task_returns_none(self, mock_runwayml):
        from cqc_lem.utilities.ai.video_models import create_runway_video
        mock_runwayml["task"].status = "FAILED"
        assert create_runway_video("https://img/base.png", "x", model="gen4_turbo") is None

    def test_unknown_model_raises(self, mock_runwayml):
        from cqc_lem.utilities.ai.video_models import create_runway_video
        with pytest.raises(ValueError):
            create_runway_video("https://img/base.png", "x", model="does-not-exist")

    def test_typeerror_retry_drops_optional_kwargs(self, mock_runwayml):
        from cqc_lem.utilities.ai.video_models import create_runway_video
        create = mock_runwayml["client"].image_to_video.create
        task = mock_runwayml["task"]
        # First call (full kwargs) raises TypeError; retry with slim kwargs succeeds.
        create.side_effect = [TypeError("unexpected duration"), task]
        url = create_runway_video("https://img/base.png", "x", model="gen4_turbo", duration=10)
        assert url == "https://runway.example/video.mp4"
        slim = create.call_args[1]
        assert "duration" not in slim and "ratio" in slim
