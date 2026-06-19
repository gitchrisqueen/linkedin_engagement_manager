"""Unit tests for post_to_linkedin task — post-type branching."""

import pytest
from contextlib import ExitStack
from unittest.mock import patch


BASE_PATCHES = [
    ("cqc_lem.app.run_automation.get_post_status", {"return_value": "approved"}),
    ("cqc_lem.app.run_automation.get_user_password_pair_by_id", {"return_value": ("u@example.com", "pw")}),
    ("cqc_lem.app.run_automation.get_post_content", {"return_value": "Post text"}),
    ("cqc_lem.app.run_automation.insert_new_log", {}),
    ("cqc_lem.app.run_automation.update_db_post_status", {}),
    ("cqc_lem.app.run_automation.automate_reply_commenting", {}),
]


@pytest.mark.unit
class TestPostToLinkedinTypeBranching:

    def test_text_post_calls_share_on_linkedin(self):
        from cqc_lem.utilities.db import PostType
        from cqc_lem.app.run_automation import post_to_linkedin

        with ExitStack() as stack:
            for target, kwargs in BASE_PATCHES:
                stack.enter_context(patch(target, **kwargs))
            stack.enter_context(patch("cqc_lem.app.run_automation.get_post_type", return_value=PostType.TEXT))
            mock_share = stack.enter_context(
                patch("cqc_lem.app.run_automation.share_on_linkedin", return_value="urn:li:ugcPost:1")
            )
            mock_carousel = stack.enter_context(
                patch("cqc_lem.app.run_automation.share_carousel_on_linkedin")
            )

            post_to_linkedin.run(1, 10)

            mock_share.assert_called_once_with(1, "Post text")
            mock_carousel.assert_not_called()

    def test_video_post_calls_share_on_linkedin_with_url(self):
        from cqc_lem.utilities.db import PostType
        from cqc_lem.app.run_automation import post_to_linkedin

        with ExitStack() as stack:
            for target, kwargs in BASE_PATCHES:
                stack.enter_context(patch(target, **kwargs))
            stack.enter_context(patch("cqc_lem.app.run_automation.get_post_type", return_value=PostType.VIDEO))
            stack.enter_context(
                patch("cqc_lem.app.run_automation.get_post_video_url", return_value="https://cdn.example.com/v.mp4")
            )
            mock_share = stack.enter_context(
                patch("cqc_lem.app.run_automation.share_on_linkedin", return_value="urn:li:ugcPost:2")
            )
            mock_carousel = stack.enter_context(
                patch("cqc_lem.app.run_automation.share_carousel_on_linkedin")
            )

            post_to_linkedin.run(1, 20)

            mock_share.assert_called_once_with(1, "Post text", "https://cdn.example.com/v.mp4")
            mock_carousel.assert_not_called()

    def test_carousel_post_calls_share_carousel_on_linkedin(self):
        from cqc_lem.utilities.db import PostType
        from cqc_lem.app.run_automation import post_to_linkedin

        slides = ["Slide one", "Slide two"]
        with ExitStack() as stack:
            for target, kwargs in BASE_PATCHES:
                stack.enter_context(patch(target, **kwargs))
            stack.enter_context(patch("cqc_lem.app.run_automation.get_post_type", return_value=PostType.CAROUSEL))
            stack.enter_context(patch("cqc_lem.app.run_automation.get_carousel_slides", return_value=slides))
            mock_carousel = stack.enter_context(
                patch("cqc_lem.app.run_automation.share_carousel_on_linkedin", return_value="urn:li:ugcPost:3")
            )
            mock_share = stack.enter_context(
                patch("cqc_lem.app.run_automation.share_on_linkedin")
            )

            post_to_linkedin.run(1, 30)

            mock_carousel.assert_called_once_with(1, "Post text", slides)
            mock_share.assert_not_called()

    def test_skips_already_posted(self):
        from cqc_lem.app.run_automation import post_to_linkedin

        with patch("cqc_lem.app.run_automation.get_post_status", return_value="posted"), \
             patch("cqc_lem.app.run_automation.share_on_linkedin") as mock_share, \
             patch("cqc_lem.app.run_automation.share_carousel_on_linkedin") as mock_carousel:

            result = post_to_linkedin.run(1, 99)

            assert "already posted" in result.lower()
            mock_share.assert_not_called()
            mock_carousel.assert_not_called()
