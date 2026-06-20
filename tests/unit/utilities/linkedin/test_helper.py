"""Unit tests for cqc_lem.utilities.linkedin.helper — login_to_linkedin."""

import pytest
from unittest.mock import MagicMock, patch, call

pytestmark = pytest.mark.unit

_MODULE = "cqc_lem.utilities.linkedin.helper"


def _make_driver(url: str) -> MagicMock:
    driver = MagicMock()
    driver.current_url = url
    driver.get_cookies.return_value = [{"name": "li_at", "value": "tok"}]
    return driver


def _make_wait() -> MagicMock:
    wait = MagicMock()
    wait.until = MagicMock()
    return wait


@pytest.mark.unit
class TestLoginToLinkedinCookiePath:
    """Tests for the cookie-based fast-path (already logged in)."""

    def _run(self, url_after_load: str, cookies=None):
        driver = _make_driver(url_after_load)
        wait = _make_wait()

        with patch(f"{_MODULE}.get_cookies", return_value=cookies or [{"name": "x"}]), \
             patch(f"{_MODULE}.load_cookies") as mock_load, \
             patch(f"{_MODULE}.store_cookies") as mock_store:
            from cqc_lem.utilities.linkedin.helper import login_to_linkedin
            login_to_linkedin(driver, wait, "test@example.com", "password")

        return driver, mock_load, mock_store

    def test_already_logged_in_feed_url(self):
        """Navigating to /feed/ with valid cookies → detected as logged in."""
        driver, _, mock_store = self._run("https://www.linkedin.com/feed/")
        # Cookies are refreshed in the DB
        mock_store.assert_called_once_with("test@example.com", driver.get_cookies())

    def test_already_logged_in_home_url(self):
        """LinkedIn /home redirect (new behaviour) → still detected as logged in."""
        driver, _, mock_store = self._run("https://www.linkedin.com/home")
        mock_store.assert_called_once()

    def test_already_logged_in_mynetwork_url(self):
        """LinkedIn /mynetwork → logged in."""
        driver, _, mock_store = self._run("https://www.linkedin.com/mynetwork/")
        mock_store.assert_called_once()

    def test_already_logged_in_jobs_url(self):
        driver, _, mock_store = self._run("https://www.linkedin.com/jobs/")
        mock_store.assert_called_once()

    def test_navigates_to_feed_after_loading_cookies(self):
        """After loading cookies, must navigate to /feed/ (not bare homepage)."""
        driver = _make_driver("https://www.linkedin.com/feed/")
        wait = _make_wait()
        get_calls = []
        driver.get.side_effect = lambda url: get_calls.append(url)

        with patch(f"{_MODULE}.get_cookies", return_value=[{"name": "x"}]), \
             patch(f"{_MODULE}.load_cookies"), \
             patch(f"{_MODULE}.store_cookies"):
            from cqc_lem.utilities.linkedin.helper import login_to_linkedin
            login_to_linkedin(driver, wait, "user@e.com", "pw")

        assert any("feed" in u for u in get_calls), (
            f"Expected a navigation to /feed/ after loading cookies, got: {get_calls}"
        )

    def test_challenge_url_after_cookies_raises(self):
        """Security challenge after cookie load → RuntimeError (not silent fail)."""
        driver = _make_driver("https://www.linkedin.com/checkpoint/challenge")
        wait = _make_wait()

        with patch(f"{_MODULE}.get_cookies", return_value=[{"name": "x"}]), \
             patch(f"{_MODULE}.load_cookies"), \
             patch(f"{_MODULE}.store_cookies"), \
             pytest.raises(RuntimeError, match="security challenge"):
            from cqc_lem.utilities.linkedin.helper import login_to_linkedin
            login_to_linkedin(driver, wait, "user@e.com", "pw")

    def test_no_cookies_goes_to_login_flow(self):
        """No stored cookies → must do credential login (navigate to /login)."""
        # After /login navigate, URL becomes the login page; after submit, /feed/
        call_count = 0
        get_urls = []

        def fake_get(url):
            get_urls.append(url)

        # Simulate: base page → challenge-free login page → feed after submit
        driver = MagicMock()
        driver.get_cookies.return_value = [{"name": "li_at"}]

        # current_url changes with each driver.get() call
        url_sequence = [
            "https://www.linkedin.com",   # initial get
            "https://www.linkedin.com/login",  # after driver.get(login_url)
            "https://www.linkedin.com/feed/",  # after submit
        ]
        get_index = [0]

        def get_url():
            return url_sequence[min(get_index[0], len(url_sequence) - 1)]

        type(driver).current_url = property(lambda self: get_url())
        driver.get.side_effect = lambda u: get_index.__setitem__(0, get_index[0] + 1)

        wait = _make_wait()
        mock_field = MagicMock()

        with patch(f"{_MODULE}.get_cookies", return_value=None), \
             patch(f"{_MODULE}.load_cookies"), \
             patch(f"{_MODULE}.store_cookies") as mock_store, \
             patch(f"{_MODULE}.get_element_wait_retry", return_value=mock_field), \
             patch(f"{_MODULE}.click_element_wait_retry"):
            from cqc_lem.utilities.linkedin.helper import login_to_linkedin
            login_to_linkedin(driver, wait, "user@e.com", "pw")

        # Must have navigated to the login page directly
        calls = [c[0][0] for c in driver.get.call_args_list]
        assert any("login" in u for u in calls), f"Expected /login navigation, got: {calls}"
        # Cookies stored after successful login
        mock_store.assert_called_once()


@pytest.mark.unit
class TestLoginToLinkedinChallengePaths:
    """Challenge URL detection must cover all known challenge path prefixes."""

    @pytest.mark.parametrize("challenge_url", [
        "https://www.linkedin.com/checkpoint/challenge/abc",
        "https://www.linkedin.com/authwall?trk=x",
        "https://www.linkedin.com/uas/login",
        "https://www.linkedin.com/challenge/",
    ])
    def test_challenge_url_after_cookie_load_raises(self, challenge_url):
        driver = _make_driver(challenge_url)
        wait = _make_wait()

        with patch(f"{_MODULE}.get_cookies", return_value=[{"name": "x"}]), \
             patch(f"{_MODULE}.load_cookies"), \
             patch(f"{_MODULE}.store_cookies"), \
             pytest.raises(RuntimeError):
            from cqc_lem.utilities.linkedin.helper import login_to_linkedin
            login_to_linkedin(driver, wait, "u@e.com", "pw")
