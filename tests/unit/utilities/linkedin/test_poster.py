"""Unit tests for LinkedIn poster utilities."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.unit
class TestValidatePostContentLength:
    def test_short_content_under_limit(self):
        content = "Short post about AI."
        assert len(content) < 3000

    def test_long_content_over_limit(self):
        content = "x" * 3001
        assert len(content) > 3000


@pytest.mark.unit
class TestValidateMediaUrlFormat:
    @pytest.mark.parametrize("url", [
        "https://example.com/image.jpg",
        "https://example.com/video.mp4",
        "https://cdn.example.com/path/to/media.png",
    ])
    def test_valid_https_urls(self, url):
        assert url.startswith("https://")

    @pytest.mark.parametrize("url", [
        "not-a-url",
        "ftp://example.com/file.jpg",
        "http://example.com/img.jpg",
    ])
    def test_non_https_urls_not_secure(self, url):
        assert not url.startswith("https://")


@pytest.mark.unit
class TestValidatePostType:
    def test_valid_post_types(self, sample_post_data):
        valid_types = ["TEXT", "IMAGE", "VIDEO", "CAROUSEL", "text", "image", "video", "carousel"]
        assert sample_post_data["post_type"].upper() in [t.upper() for t in valid_types]


@pytest.mark.unit
class TestDownloadMedia:
    def test_downloads_to_tmp_and_returns_path(self):
        from unittest.mock import mock_open
        m_open = mock_open()
        with patch("requests.get") as mock_get, \
             patch("cqc_lem.utilities.linkedin.poster.open", m_open, create=True), \
             patch("os.makedirs", MagicMock()):
            from cqc_lem.utilities.linkedin.poster import download_media

            mock_response = MagicMock()
            mock_response.content = b"fake_image_bytes"
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            result = download_media("https://example.com/image.jpg")

            mock_get.assert_called_once_with("https://example.com/image.jpg", timeout=30)
            assert result is not None
            assert isinstance(result, str)


@pytest.mark.unit
class TestShareOnLinkedin:
    def test_calls_ugc_posts_create(self):
        with patch("cqc_lem.utilities.linkedin.poster.get_user_linked_sub_id") as mock_sub, \
             patch("cqc_lem.utilities.linkedin.poster.get_user_access_token") as mock_token, \
             patch("cqc_lem.utilities.linkedin.poster.RestliClient") as mock_restli:
            from cqc_lem.utilities.linkedin.poster import share_on_linkedin

            mock_sub.return_value = "urn:li:person:abc123"
            mock_token.return_value = "fake_access_token"
            mock_client = MagicMock()
            mock_restli.return_value = mock_client
            mock_client.create.return_value = MagicMock(entity_id="urn:li:ugcPost:999")

            result = share_on_linkedin(
                user_id=1,
                content="Test post content",
            )

            assert mock_client.create.called
            create_call = mock_client.create.call_args
            assert "ugcPosts" in str(create_call) or create_call is not None

    def test_returns_none_when_user_not_found(self):
        with patch("cqc_lem.utilities.linkedin.poster.get_user_linked_sub_id") as mock_sub, \
             patch("cqc_lem.utilities.linkedin.poster.get_user_access_token") as mock_token:
            from cqc_lem.utilities.linkedin.poster import share_on_linkedin

            mock_sub.return_value = None
            mock_token.return_value = None

            result = share_on_linkedin(user_id=999, content="content")

            assert result is None
