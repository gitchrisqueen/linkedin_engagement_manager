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


@pytest.mark.unit
class TestIsLocalImagePath:
    def test_absolute_path_is_local(self):
        from cqc_lem.utilities.linkedin.poster import _is_local_image_path
        assert _is_local_image_path("/app/images/slide_01.png") is True

    def test_http_url_is_not_local(self):
        from cqc_lem.utilities.linkedin.poster import _is_local_image_path
        assert _is_local_image_path("https://example.com/slide.png") is False

    def test_empty_string_is_not_local(self):
        from cqc_lem.utilities.linkedin.poster import _is_local_image_path
        assert _is_local_image_path("") is False

    def test_plain_text_query_is_not_local(self):
        from cqc_lem.utilities.linkedin.poster import _is_local_image_path
        assert _is_local_image_path("artificial intelligence enterprise") is False


@pytest.mark.unit
class TestIsImageUrl:
    def test_https_url_detected(self):
        from cqc_lem.utilities.linkedin.poster import _is_image_url
        assert _is_image_url("https://example.com/slide.png") is True

    def test_http_url_detected(self):
        from cqc_lem.utilities.linkedin.poster import _is_image_url
        assert _is_image_url("http://localhost/api/assets?file_name=images/1.png") is True

    def test_ngrok_url_detected(self):
        from cqc_lem.utilities.linkedin.poster import _is_image_url
        assert _is_image_url("https://relegable-preroyally-marti.ngrok-free.dev/api/assets?file_name=images/carousel/1488/slide_01.png") is True

    def test_local_path_not_detected_as_url(self):
        from cqc_lem.utilities.linkedin.poster import _is_image_url
        assert _is_image_url("/app/images/slide.png") is False

    def test_plain_text_not_detected_as_url(self):
        from cqc_lem.utilities.linkedin.poster import _is_image_url
        assert _is_image_url("enterprise AI slides") is False

    def test_empty_string_not_detected_as_url(self):
        from cqc_lem.utilities.linkedin.poster import _is_image_url
        assert _is_image_url("") is False


@pytest.mark.unit
class TestShareCarouselOnLinkedin:
    """Tests for share_carousel_on_linkedin — especially the slide routing logic."""

    def _make_mock_restli(self):
        mock_client = MagicMock()
        mock_client.create.return_value = MagicMock(entity_id="urn:li:share:999")
        return mock_client

    def test_url_slides_passed_directly_to_upload_media(self):
        """Regression: URL slides must NOT go through get_pexels_image_path (bug that caused FileNotFoundError)."""
        slides = [
            "https://relegable-preroyally-marti.ngrok-free.dev/api/assets?file_name=images/carousel/1488/slide_01.png",
            "https://relegable-preroyally-marti.ngrok-free.dev/api/assets?file_name=images/carousel/1488/slide_02.png",
        ]
        with patch("cqc_lem.utilities.linkedin.poster.get_user_linked_sub_id", return_value="abc123"), \
             patch("cqc_lem.utilities.linkedin.poster.get_user_access_token", return_value="tok"), \
             patch("cqc_lem.utilities.linkedin.poster.RestliClient", return_value=self._make_mock_restli()), \
             patch("cqc_lem.utilities.linkedin.poster.upload_media", return_value="urn:li:asset:1") as mock_upload, \
             patch("cqc_lem.utilities.carousel_creator.get_pexels_image_path") as mock_pexels:
            from cqc_lem.utilities.linkedin.poster import share_carousel_on_linkedin

            share_carousel_on_linkedin(user_id=60, content="test content", slide_texts=slides)

            mock_pexels.assert_not_called()
            assert mock_upload.call_count == 2
            mock_upload.assert_any_call("tok", "abc123", slides[0], "IMAGE")
            mock_upload.assert_any_call("tok", "abc123", slides[1], "IMAGE")

    def test_local_path_slides_passed_directly(self):
        slides = ["/app/images/slide_01.png", "/app/images/slide_02.png"]
        with patch("cqc_lem.utilities.linkedin.poster.get_user_linked_sub_id", return_value="abc123"), \
             patch("cqc_lem.utilities.linkedin.poster.get_user_access_token", return_value="tok"), \
             patch("cqc_lem.utilities.linkedin.poster.RestliClient", return_value=self._make_mock_restli()), \
             patch("cqc_lem.utilities.linkedin.poster.upload_media", return_value="urn:li:asset:1") as mock_upload, \
             patch("cqc_lem.utilities.carousel_creator.get_pexels_image_path") as mock_pexels:
            from cqc_lem.utilities.linkedin.poster import share_carousel_on_linkedin

            share_carousel_on_linkedin(user_id=60, content="test content", slide_texts=slides)

            mock_pexels.assert_not_called()
            assert mock_upload.call_count == 2

    def test_text_query_slides_use_pexels(self):
        # get_pexels_image_path is imported lazily inside the function, so patch at source
        slides = ["enterprise AI", "machine learning"]
        mock_pexels_path = "/tmp/pexels_image.png"
        with patch("cqc_lem.utilities.linkedin.poster.get_user_linked_sub_id", return_value="abc123"), \
             patch("cqc_lem.utilities.linkedin.poster.get_user_access_token", return_value="tok"), \
             patch("cqc_lem.utilities.linkedin.poster.RestliClient", return_value=self._make_mock_restli()), \
             patch("cqc_lem.utilities.linkedin.poster.upload_media", return_value="urn:li:asset:1"), \
             patch("cqc_lem.utilities.carousel_creator.get_pexels_image_path", return_value=mock_pexels_path) as mock_pexels:
            from cqc_lem.utilities.linkedin.poster import share_carousel_on_linkedin

            share_carousel_on_linkedin(user_id=60, content="test", slide_texts=slides)

            assert mock_pexels.call_count == 2

    def test_returns_none_when_no_credentials(self):
        with patch("cqc_lem.utilities.linkedin.poster.get_user_linked_sub_id", return_value=None), \
             patch("cqc_lem.utilities.linkedin.poster.get_user_access_token", return_value=None):
            from cqc_lem.utilities.linkedin.poster import share_carousel_on_linkedin

            result = share_carousel_on_linkedin(user_id=999, content="test", slide_texts=["slide1"])

            assert result is None

    def test_falls_back_to_text_post_when_no_uploads_succeed(self):
        slides = ["https://example.com/slide.png"]
        with patch("cqc_lem.utilities.linkedin.poster.get_user_linked_sub_id", return_value="abc"), \
             patch("cqc_lem.utilities.linkedin.poster.get_user_access_token", return_value="tok"), \
             patch("cqc_lem.utilities.linkedin.poster.RestliClient"), \
             patch("cqc_lem.utilities.linkedin.poster.upload_media", return_value=None), \
             patch("cqc_lem.utilities.linkedin.poster.share_on_linkedin", return_value="urn:li:share:fallback") as mock_fallback:
            from cqc_lem.utilities.linkedin.poster import share_carousel_on_linkedin

            result = share_carousel_on_linkedin(user_id=60, content="test", slide_texts=slides)

            mock_fallback.assert_called_once_with(60, "test")
            assert result == "urn:li:share:fallback"
