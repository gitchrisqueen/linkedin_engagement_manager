"""Unit tests for tier selection + credit lifecycle in the video pipeline."""

import pytest
from unittest.mock import patch

pytestmark = pytest.mark.unit


class TestPremiumTier:
    def test_mapping(self):
        from cqc_lem.app.run_content_plan import _premium_tier_for_quality
        assert _premium_tier_for_quality("standard") is None
        assert _premium_tier_for_quality("unknown") is None
        m, c, a = _premium_tier_for_quality("premium")
        assert c == 1 and a is True
        m, c, a = _premium_tier_for_quality("premium_top")
        assert c == 3 and a is True


class TestGenerateVideoSrc:
    def test_premium_no_credits_falls_back_to_standard(self):
        with patch("cqc_lem.utilities.db.get_post_video_quality", return_value="premium"), \
             patch("cqc_lem.utilities.db.get_video_credit_balance", return_value=0), \
             patch("cqc_lem.utilities.db.deduct_video_credits") as ded, \
             patch("cqc_lem.utilities.db.get_active_avatar", return_value=None), \
             patch("cqc_lem.app.run_content_plan.get_flux_image_prompt_from_ai", return_value="scene"), \
             patch("cqc_lem.app.run_content_plan.generate_flux1_image_from_prompt", return_value="/tmp/i.png"), \
             patch("cqc_lem.app.run_content_plan.get_runway_ml_video_prompt_from_ai", return_value="motion"), \
             patch("cqc_lem.app.run_content_plan.create_runway_video", return_value="https://x.mp4") as crv:
            from cqc_lem.app.run_content_plan import _generate_video_src
            src = _generate_video_src(1, "text", None, post_id=9)
        ded.assert_not_called()
        assert src == "https://x.mp4"
        assert crv.call_args[1]["model"] == "gen4_turbo"  # standard fallback

    def test_premium_success_deducts_not_refunds(self):
        with patch("cqc_lem.utilities.db.get_post_video_quality", return_value="premium"), \
             patch("cqc_lem.utilities.db.get_video_credit_balance", return_value=5), \
             patch("cqc_lem.utilities.db.deduct_video_credits", return_value=True) as ded, \
             patch("cqc_lem.utilities.db.refund_video_credits") as ref, \
             patch("cqc_lem.utilities.db.get_active_avatar", return_value=None), \
             patch("cqc_lem.app.run_content_plan.get_flux_image_prompt_from_ai", return_value="scene"), \
             patch("cqc_lem.app.run_content_plan.get_runway_ml_video_prompt_from_ai", return_value="motion"), \
             patch("cqc_lem.app.run_content_plan.create_runway_video", return_value="https://x.mp4") as crv:
            from cqc_lem.app.run_content_plan import _generate_video_src
            src = _generate_video_src(1, "text", None, post_id=9)
        assert src == "https://x.mp4"
        ded.assert_called_once()
        ref.assert_not_called()
        # premium + no avatar -> text->video (first positional image arg is None) with audio
        assert crv.call_args[0][0] is None
        assert crv.call_args[1]["model"] == "veo3.1_fast" and crv.call_args[1]["audio"] is True

    def test_failure_refunds_and_pexels_fallback(self):
        with patch("cqc_lem.utilities.db.get_post_video_quality", return_value="premium"), \
             patch("cqc_lem.utilities.db.get_video_credit_balance", return_value=5), \
             patch("cqc_lem.utilities.db.deduct_video_credits", return_value=True), \
             patch("cqc_lem.utilities.db.refund_video_credits") as ref, \
             patch("cqc_lem.utilities.db.get_active_avatar", return_value=None), \
             patch("cqc_lem.app.run_content_plan.get_flux_image_prompt_from_ai", return_value="scene"), \
             patch("cqc_lem.app.run_content_plan.get_runway_ml_video_prompt_from_ai", return_value="motion"), \
             patch("cqc_lem.app.run_content_plan.create_runway_video", side_effect=RuntimeError("boom")), \
             patch("cqc_lem.app.run_content_plan.create_folder_if_not_exists"), \
             patch("cqc_lem.utilities.pexels_helper.download_pexels_video", return_value="/tmp/p.mp4", create=True):
            from cqc_lem.app.run_content_plan import _generate_video_src
            src = _generate_video_src(1, "text", None, post_id=9)
        ref.assert_called_once()
        assert src == "/tmp/p.mp4"

    def test_standard_quality_no_credit_calls(self):
        with patch("cqc_lem.utilities.db.get_post_video_quality", return_value="standard"), \
             patch("cqc_lem.utilities.db.get_video_credit_balance") as bal, \
             patch("cqc_lem.utilities.db.deduct_video_credits") as ded, \
             patch("cqc_lem.utilities.db.get_active_avatar", return_value=None), \
             patch("cqc_lem.app.run_content_plan.get_flux_image_prompt_from_ai", return_value="scene"), \
             patch("cqc_lem.app.run_content_plan.generate_flux1_image_from_prompt", return_value="/tmp/i.png"), \
             patch("cqc_lem.app.run_content_plan.get_runway_ml_video_prompt_from_ai", return_value="motion"), \
             patch("cqc_lem.app.run_content_plan.create_runway_video", return_value="https://x.mp4") as crv:
            from cqc_lem.app.run_content_plan import _generate_video_src
            src = _generate_video_src(1, "text", None, post_id=9)
        bal.assert_not_called()
        ded.assert_not_called()
        assert crv.call_args[1]["model"] == "gen4_turbo"
