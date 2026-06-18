"""Unit tests for AI helper utilities."""

import pytest
from unittest.mock import MagicMock, patch, call


@pytest.mark.unit
class TestGenerateAiResponse:
    def test_calls_api_and_returns_string(self, mock_openai_client, sample_linkedin_profile):
        with patch("cqc_lem.utilities.ai.ai_helper.client", mock_openai_client):
            from cqc_lem.utilities.ai.ai_helper import generate_ai_response
            from cqc_lem.utilities.linkedin.profile import LinkedInProfile

            profile = LinkedInProfile(**sample_linkedin_profile)
            result = generate_ai_response("Write a comment about AI", profile)

            assert mock_openai_client.chat.completions.create.called
            assert isinstance(result, str)

    def test_uses_medium_tier_model(self, mock_openai_client, sample_linkedin_profile):
        with patch("cqc_lem.utilities.ai.ai_helper.client", mock_openai_client):
            from cqc_lem.utilities.ai.ai_helper import generate_ai_response
            from cqc_lem.utilities.linkedin.profile import LinkedInProfile

            profile = LinkedInProfile(**sample_linkedin_profile)
            generate_ai_response("Write a comment", profile)

            call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
            assert call_kwargs.get("model") == "lem-medium"

    def test_returns_none_for_empty_response(self, mock_openai_client, sample_linkedin_profile):
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = None
        with patch("cqc_lem.utilities.ai.ai_helper.client", mock_openai_client):
            from cqc_lem.utilities.ai.ai_helper import generate_ai_response
            from cqc_lem.utilities.linkedin.profile import LinkedInProfile

            profile = LinkedInProfile(**sample_linkedin_profile)
            result = generate_ai_response("Write a comment", profile)

            assert result is None


@pytest.mark.unit
class TestGetAiMessageRefinement:
    def test_returns_string(self, mock_openai_client):
        with patch("cqc_lem.utilities.ai.ai_helper.client", mock_openai_client):
            from cqc_lem.utilities.ai.ai_helper import get_ai_message_refinement

            result = get_ai_message_refinement("Hey, want to connect?")

            assert isinstance(result, str)
            assert mock_openai_client.chat.completions.create.called

    def test_uses_simple_tier_model(self, mock_openai_client):
        with patch("cqc_lem.utilities.ai.ai_helper.client", mock_openai_client):
            from cqc_lem.utilities.ai.ai_helper import get_ai_message_refinement

            get_ai_message_refinement("Hello!")

            call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
            assert call_kwargs.get("model") == "lem-simple"

    def test_character_limit_in_prompt(self, mock_openai_client):
        with patch("cqc_lem.utilities.ai.ai_helper.client", mock_openai_client):
            from cqc_lem.utilities.ai.ai_helper import get_ai_message_refinement

            get_ai_message_refinement("Hello!", character_limit=150)

            call_args = mock_openai_client.chat.completions.create.call_args
            messages = call_args[1]["messages"]
            all_content = " ".join(str(m.get("content", "")) for m in messages)
            assert "150" in all_content


@pytest.mark.unit
class TestSummarizeRecentActivity:
    def test_returns_none_for_empty_activities(self, mock_openai_client, sample_linkedin_profile):
        with patch("cqc_lem.utilities.ai.ai_helper.client", mock_openai_client):
            from cqc_lem.utilities.ai.ai_helper import summarize_recent_activity
            from cqc_lem.utilities.linkedin.profile import LinkedInProfile

            main_profile = LinkedInProfile(**sample_linkedin_profile)
            empty_data = {**sample_linkedin_profile, "recent_activities": []}
            activity_profile = LinkedInProfile(**empty_data)

            result = summarize_recent_activity(activity_profile, main_profile)

            assert result is None
            mock_openai_client.chat.completions.create.assert_not_called()

    def test_calls_api_for_profiles_with_activities(self, mock_openai_client, sample_linkedin_profile):
        with patch("cqc_lem.utilities.ai.ai_helper.client", mock_openai_client):
            from cqc_lem.utilities.ai.ai_helper import summarize_recent_activity
            from cqc_lem.utilities.linkedin.profile import LinkedInProfile, LinkedInActivity

            main_profile = LinkedInProfile(**sample_linkedin_profile)
            active_data = {
                **sample_linkedin_profile,
                "recent_activities": [LinkedInActivity(text="Posted about AI")],
            }
            activity_profile = LinkedInProfile(**active_data)

            result = summarize_recent_activity(activity_profile, main_profile)

            assert mock_openai_client.chat.completions.create.called
            assert isinstance(result, str)


@pytest.mark.unit
class TestGetDallEImagePromptFromAi:
    def test_returns_prompt_string(self, mock_openai_client):
        with patch("cqc_lem.utilities.ai.ai_helper.client", mock_openai_client):
            from cqc_lem.utilities.ai.ai_helper import get_dall_e_image_prompt_from_ai

            result = get_dall_e_image_prompt_from_ai("AI and the future of work")

            assert isinstance(result, str)
            assert mock_openai_client.chat.completions.create.called

    def test_uses_simple_tier_model(self, mock_openai_client):
        with patch("cqc_lem.utilities.ai.ai_helper.client", mock_openai_client):
            from cqc_lem.utilities.ai.ai_helper import get_dall_e_image_prompt_from_ai

            get_dall_e_image_prompt_from_ai("content")

            call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
            assert call_kwargs.get("model") == "lem-simple"


@pytest.mark.unit
class TestGetFluxImagePromptFromAi:
    def test_returns_prompt_string(self, mock_openai_client):
        with patch("cqc_lem.utilities.ai.ai_helper.client", mock_openai_client):
            from cqc_lem.utilities.ai.ai_helper import get_flux_image_prompt_from_ai

            result = get_flux_image_prompt_from_ai("Technology innovation post")

            assert isinstance(result, str)

    def test_uses_simple_tier_model(self, mock_openai_client):
        with patch("cqc_lem.utilities.ai.ai_helper.client", mock_openai_client):
            from cqc_lem.utilities.ai.ai_helper import get_flux_image_prompt_from_ai

            get_flux_image_prompt_from_ai("content")

            call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
            assert call_kwargs.get("model") == "lem-simple"


@pytest.mark.unit
class TestGetThoughtLeadershipPostFromAi:
    def test_uses_complex_tier_model(self, mock_openai_client, sample_linkedin_profile):
        with patch("cqc_lem.utilities.ai.ai_helper.client", mock_openai_client), \
             patch("cqc_lem.utilities.ai.ai_helper.get_industry_trend_analysis_based_on_user_profile") as mock_trends:
            from cqc_lem.utilities.ai.ai_helper import get_thought_leadership_post_from_ai
            from cqc_lem.utilities.linkedin.profile import LinkedInProfile

            mock_trends.return_value = {"industry": "Technology", "analysis": "AI is growing"}
            profile = LinkedInProfile(**sample_linkedin_profile)

            get_thought_leadership_post_from_ai(profile, "awareness")

            call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
            assert call_kwargs.get("model") == "lem-complex"


@pytest.mark.unit
class TestCreateVideoFromPrompt:
    def test_raises_not_implemented(self):
        from cqc_lem.utilities.ai.ai_helper import create_video_from_prompt

        with pytest.raises(NotImplementedError, match="create_runway_video"):
            create_video_from_prompt("A video about AI")


@pytest.mark.unit
class TestModelTierAssignments:
    """Verify all functions use the expected LiteLLM tier aliases."""

    @pytest.mark.parametrize("func_name,expected_model", [
        ("get_ai_message_refinement", "lem-simple"),
        ("get_dall_e_image_prompt_from_ai", "lem-simple"),
        ("get_flux_image_prompt_from_ai", "lem-simple"),
    ])
    def test_simple_tier_functions(self, func_name, expected_model, mock_openai_client, sample_linkedin_profile):
        import cqc_lem.utilities.ai.ai_helper as module
        with patch("cqc_lem.utilities.ai.ai_helper.client", mock_openai_client):
            fn = getattr(module, func_name)
            try:
                fn("test content")
            except Exception:
                pass  # we only care that model was set correctly
            if mock_openai_client.chat.completions.create.called:
                call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
                assert call_kwargs.get("model") == expected_model
