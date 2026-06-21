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
             pytest.raises(RuntimeError, match="Unsolvable LinkedIn challenge"):
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
class TestSolveArkoseChallenge:
    """Unit tests for solve_arkose_challenge() in linkedin/helper.py."""

    def _make_driver(self, iframes=None):
        driver = MagicMock()
        driver.current_url = "https://www.linkedin.com/checkpoint/challenge"
        driver.find_elements.return_value = iframes or []
        driver.page_source = "<html></html>"
        return driver

    def _make_arkose_iframe(self, src="https://client-api.arkoselabs.com/fc/assets/"):
        frame = MagicMock()
        frame.get_attribute.return_value = src
        return frame

    def test_returns_false_when_api_key_not_set(self, monkeypatch):
        """No CAPSOLVER_API_KEY → False immediately (no API call attempted)."""
        monkeypatch.delenv("CAPSOLVER_API_KEY", raising=False)
        driver = self._make_driver()
        wait = _make_wait()

        from cqc_lem.utilities.linkedin.helper import solve_arkose_challenge
        result = solve_arkose_challenge(driver, wait)

        assert result is False
        driver.find_elements.assert_not_called()

    def test_returns_false_when_api_key_is_empty(self, monkeypatch):
        monkeypatch.setenv("CAPSOLVER_API_KEY", "")
        driver = self._make_driver()
        wait = _make_wait()

        from cqc_lem.utilities.linkedin.helper import solve_arkose_challenge
        assert solve_arkose_challenge(driver, wait) is False

    def test_returns_false_when_no_arkose_iframe(self, monkeypatch):
        """Page has no Arkose Labs iframe → False, no capsolver call."""
        monkeypatch.setenv("CAPSOLVER_API_KEY", "CAP-test-key-abc123")
        driver = self._make_driver(iframes=[])
        wait = _make_wait()

        with patch(f"{_MODULE}.capsolver", create=True):
            from cqc_lem.utilities.linkedin.helper import solve_arkose_challenge
            result = solve_arkose_challenge(driver, wait)

        assert result is False

    def test_returns_false_when_iframe_has_no_arkoselabs_src(self, monkeypatch):
        """Iframe present but not from arkoselabs.com → not an Arkose challenge."""
        monkeypatch.setenv("CAPSOLVER_API_KEY", "CAP-test-key-abc123")
        non_arkose = MagicMock()
        non_arkose.get_attribute.return_value = "https://other.com/captcha"
        driver = self._make_driver(iframes=[non_arkose])
        wait = _make_wait()

        from cqc_lem.utilities.linkedin.helper import solve_arkose_challenge
        assert solve_arkose_challenge(driver, wait) is False

    def test_returns_false_when_capsolver_raises(self, monkeypatch):
        """capsolver.solve() raises an exception → False (logged warning, no crash)."""
        monkeypatch.setenv("CAPSOLVER_API_KEY", "CAP-test-key-abc123")
        arkose = self._make_arkose_iframe(
            "https://client-api.arkoselabs.com/fc/?pk=ABCD-1234&surl=https://client-api.arkoselabs.com/"
        )
        driver = self._make_driver(iframes=[arkose])
        wait = _make_wait()

        mock_capsolver = MagicMock()
        mock_capsolver.solve.side_effect = RuntimeError("API unreachable")

        with patch.dict("sys.modules", {"capsolver": mock_capsolver}):
            from importlib import reload
            import cqc_lem.utilities.linkedin.helper as helper_mod
            reload(helper_mod)
            result = helper_mod.solve_arkose_challenge(driver, wait)

        assert result is False

    def test_returns_false_when_capsolver_returns_empty_token(self, monkeypatch):
        """capsolver.solve() returns a dict with no token → False."""
        monkeypatch.setenv("CAPSOLVER_API_KEY", "CAP-test-key-abc123")
        arkose = self._make_arkose_iframe(
            "https://client-api.arkoselabs.com/fc/?pk=ABCD-1234&surl=https://client-api.arkoselabs.com/"
        )
        driver = self._make_driver(iframes=[arkose])
        wait = _make_wait()

        mock_capsolver = MagicMock()
        mock_capsolver.solve.return_value = {"token": ""}

        with patch.dict("sys.modules", {"capsolver": mock_capsolver}):
            from importlib import reload
            import cqc_lem.utilities.linkedin.helper as helper_mod
            reload(helper_mod)
            result = helper_mod.solve_arkose_challenge(driver, wait)

        assert result is False

    def test_returns_true_and_injects_token_when_solved(self, monkeypatch):
        """Valid Arkose iframe + capsolver returns token → True, token injected via JS."""
        monkeypatch.setenv("CAPSOLVER_API_KEY", "CAP-test-key-abc123")
        arkose = self._make_arkose_iframe(
            "https://client-api.arkoselabs.com/fc/?pk=LI-TEST-KEY&surl=https://client-api.arkoselabs.com/"
        )
        driver = self._make_driver(iframes=[arkose])
        driver.find_elements.return_value = [arkose]
        wait = _make_wait()

        token = "2.abc123.challenge_token_value"
        mock_capsolver = MagicMock()
        mock_capsolver.solve.return_value = {"token": token}

        with patch.dict("sys.modules", {"capsolver": mock_capsolver}):
            from importlib import reload
            import cqc_lem.utilities.linkedin.helper as helper_mod
            reload(helper_mod)
            result = helper_mod.solve_arkose_challenge(driver, wait)

        assert result is True
        # Token must be injected via JS
        js_calls = [str(c) for c in driver.execute_script.call_args_list]
        assert any(token in call for call in js_calls), (
            f"Expected token '{token}' injected via execute_script, got: {js_calls}"
        )


@pytest.mark.unit
class TestLoginToLinkedinPostSubmitChallenge:
    """Post-submit challenge detection (new behaviour after login button click)."""

    def test_post_submit_challenge_calls_solver(self):
        """After submit, if URL is a challenge page, solve_arkose_challenge is invoked."""
        url_seq = [
            "https://www.linkedin.com",        # initial load
            "https://www.linkedin.com/login",  # after driver.get(login_url)
            "https://www.linkedin.com/checkpoint/challenge",  # after submit
        ]
        idx = [0]

        driver = MagicMock()
        driver.get_cookies.return_value = [{"name": "li_at"}]
        driver.find_elements.return_value = []  # no Arkose iframe

        def advance_url(url=None):
            idx[0] = min(idx[0] + 1, len(url_seq) - 1)

        type(driver).current_url = property(lambda self: url_seq[idx[0]])
        driver.get.side_effect = advance_url
        driver.find_element.return_value = MagicMock()

        wait = _make_wait()
        mock_field = MagicMock()

        with patch(f"{_MODULE}.get_cookies", return_value=None), \
             patch(f"{_MODULE}.load_cookies"), \
             patch(f"{_MODULE}.store_cookies"), \
             patch(f"{_MODULE}.get_element_wait_retry", return_value=mock_field), \
             patch(f"{_MODULE}.click_element_wait_retry", side_effect=advance_url), \
             patch(f"{_MODULE}.solve_arkose_challenge", return_value=False) as mock_solve:
            with pytest.raises(RuntimeError, match="Unsolvable LinkedIn challenge"):
                from cqc_lem.utilities.linkedin.helper import login_to_linkedin
                login_to_linkedin(driver, wait, "user@e.com", "pw")

        mock_solve.assert_called_once()

    def test_new_challenge_paths_detected(self):
        """Newly added challenge paths (/captcha/, /security-verification) are caught."""
        for challenge_path in ["/captcha/", "/security-verification", "/error"]:
            url = f"https://www.linkedin.com{challenge_path}"
            driver = _make_driver(url)
            wait = _make_wait()

            with patch(f"{_MODULE}.get_cookies", return_value=[{"name": "x"}]), \
                 patch(f"{_MODULE}.load_cookies"), \
                 patch(f"{_MODULE}.store_cookies"), \
                 pytest.raises(RuntimeError):
                from cqc_lem.utilities.linkedin.helper import login_to_linkedin
                login_to_linkedin(driver, wait, "u@e.com", "pw")


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
