"""The P0 trial cohort cap and its join-the-list form (issue #2377).

While the launch phase is P0, a NEW account is created only while fewer than
`P0_TRIAL_COHORT_CAP` self-serve trial accounts exist. Past the cap — or whenever the count cannot
be read — the signup path answers `{"waitlist": true}` instead of an account, and no PIN email is
sent to an address that cannot get one. P1 and P2 never read the counter.

The acceptance tests run the REAL `trial_cohort_slot` against a fake MySQL connection whose
`COUNT(*)` is a counter the patched `add_user_by_email` increments, so "the 25th succeeds and the
26th gets the list" is decided by the same lock-count-insert sequence production runs.
"""

from typing import Any, Optional
from unittest.mock import MagicMock, patch

import mysql.connector
import pytest

pytestmark = pytest.mark.unit

_AUTH = "cqc_lem.api.routers.auth"
_USERS = "cqc_lem.platform.db.repositories.users"
_PHASE = "cqc_lem.utilities.brand_account.LAUNCH_PHASE"
INIT = "/api/auth/email/init"
VERIFY = "/api/auth/email/verify"
WAITLIST = "/api/auth/waitlist"


class _FakeCohortDb:
    """A MySQL stand-in that answers the three statements `trial_cohort_slot` runs.

    `members` is the cohort count; `lock_answer` is what GET_LOCK returns (1 held, 0 timed out,
    None error). Every statement is recorded so a test can assert the lock was released.
    """

    def __init__(self, members: int = 0, lock_answer: Optional[int] = 1,
                 count_error: Optional[Exception] = None) -> None:
        self.members = members
        self.lock_answer = lock_answer
        self.count_error = count_error
        self.statements: list[str] = []
        self.closed = 0

    def connection(self) -> MagicMock:
        conn = MagicMock()
        cursor = MagicMock()
        last: dict[str, Any] = {}

        def execute(sql: str, params: Any = None) -> None:
            self.statements.append(sql)
            if "COUNT(*)" in sql and self.count_error is not None:
                raise self.count_error
            last["sql"] = sql

        def fetchone() -> tuple:
            sql = last.get("sql", "")
            if "GET_LOCK" in sql:
                return (self.lock_answer,)
            if "COUNT(*)" in sql:
                return (self.members,)
            return (1,)

        def close() -> None:
            self.closed += 1

        cursor.execute.side_effect = execute
        cursor.fetchone.side_effect = fetchone
        conn.cursor.return_value = cursor
        conn.close.side_effect = close
        return conn


@pytest.fixture(autouse=True)
def _auth_side_effects():
    """DB calls the signup flow makes that are not what this suite is about."""
    with patch(f"{_AUTH}.record_auth_event", return_value=True), \
         patch(f"{_AUTH}.mark_email_verified", return_value=True), \
         patch(f"{_AUTH}.get_pin_lockout", return_value=None), \
         patch(f"{_AUTH}.get_user_public_uid", return_value="pub-uid-1"), \
         patch(f"{_AUTH}.track_funnel_event"), \
         patch(f"{_AUTH}._start_affiliate_membership"), \
         patch(f"{_AUTH}.P0_TRIAL_COHORT_CAP", 25):
        yield


def _verify(api_client: Any, db: _FakeCohortDb, email: str, phase: str = "P0") -> Any:
    """POST a correct PIN for a brand-new address, with the fake cohort DB behind the lock."""
    created: list[str] = []

    def add_user(address: str) -> int:
        created.append(address)
        db.members += 1
        return 1000 + db.members

    with patch(_PHASE, phase), \
         patch(f"{_USERS}._connection.get_db_connection", side_effect=db.connection), \
         patch(f"{_AUTH}.hash_pin", return_value="h"), \
         patch(f"{_AUTH}.verify_pin_for_email", return_value=True), \
         patch(f"{_AUTH}.get_user_id", return_value=None), \
         patch(f"{_AUTH}.add_user_by_email", side_effect=add_user), \
         patch(f"{_AUTH}.create_session", return_value="sess-new") as create_session:
        resp = api_client.post(VERIFY, json={"email": email, "pin": "123456"})
    resp.created = created
    resp.create_session = create_session
    return resp


class TestTheTwentyFifthSignupSucceedsAndTheTwentySixthGetsTheList:
    def test_twenty_five_accounts_then_the_list(self, api_client, signed_in):
        db = _FakeCohortDb(members=0)
        for n in range(1, 26):
            resp = _verify(api_client, db, f"user{n}@example.com")
            assert resp.status_code == 200
            assert resp.json()["detail"]["session_token"] == "sess-new", f"signup {n} was refused"
        assert db.members == 25

        resp = _verify(api_client, db, "user26@example.com")
        assert resp.status_code == 200
        detail = resp.json()["detail"]
        assert detail == {"waitlist": True, "email": "user26@example.com"}
        assert resp.created == []
        resp.create_session.assert_not_called()
        assert "session_token" not in detail
        assert db.members == 25

    def test_the_twenty_fifth_signup_is_created(self, api_client, signed_in):
        resp = _verify(api_client, _FakeCohortDb(members=24), "twentyfifth@example.com")
        assert resp.json()["detail"]["session_token"] == "sess-new"
        assert resp.created == ["twentyfifth@example.com"]

    def test_the_twenty_sixth_signup_gets_the_list_and_no_cookie(self, api_client, signed_in):
        resp = _verify(api_client, _FakeCohortDb(members=25), "twentysixth@example.com")
        assert resp.json()["detail"]["waitlist"] is True
        assert resp.created == []
        from cqc_lem.utilities.env_constants import SESSION_COOKIE_NAME

        assert SESSION_COOKIE_NAME not in resp.headers.get("set-cookie", "")

    def test_the_lock_is_taken_before_the_count_and_released_after(self, api_client, signed_in):
        db = _FakeCohortDb(members=3)
        _verify(api_client, db, "lock@example.com")
        kinds = [("GET_LOCK" in s and "get") or ("COUNT(*)" in s and "count")
                 or ("RELEASE_LOCK" in s and "release") for s in db.statements]
        assert kinds == ["get", "count", "release"]
        assert db.closed == 1


class TestACounterReadFailureFailsClosed:
    def test_a_connection_fault_gives_the_list(self, api_client, signed_in):
        with patch(_PHASE, "P0"), \
             patch(f"{_USERS}._connection.get_db_connection",
                   side_effect=mysql.connector.Error("down")), \
             patch(f"{_AUTH}.hash_pin", return_value="h"), \
             patch(f"{_AUTH}.verify_pin_for_email", return_value=True), \
             patch(f"{_AUTH}.get_user_id", return_value=None), \
             patch(f"{_AUTH}.add_user_by_email") as add_user, \
             patch(f"{_AUTH}.create_session") as create_session:
            resp = api_client.post(VERIFY, json={"email": "a@example.com", "pin": "123456"})
        assert resp.status_code == 200
        assert resp.json()["detail"]["waitlist"] is True
        add_user.assert_not_called()
        create_session.assert_not_called()

    def test_a_failing_count_query_gives_the_list(self, api_client, signed_in):
        db = _FakeCohortDb(members=0, count_error=mysql.connector.Error("boom"))
        resp = _verify(api_client, db, "b@example.com")
        assert resp.json()["detail"]["waitlist"] is True
        assert resp.created == []
        assert db.closed == 1

    @pytest.mark.parametrize("lock_answer", [0, None])
    def test_a_lock_not_granted_gives_the_list(self, api_client, signed_in, lock_answer):
        db = _FakeCohortDb(members=0, lock_answer=lock_answer)
        resp = _verify(api_client, db, "c@example.com")
        assert resp.json()["detail"]["waitlist"] is True
        assert resp.created == []
        # The count is never read without the lock, and an ungranted lock is never released.
        assert not any("COUNT(*)" in s or "RELEASE_LOCK" in s for s in db.statements)

    def test_an_unreadable_count_at_pin_request_sends_no_pin(self, api_client):
        with patch(_PHASE, "P0"), \
             patch(f"{_AUTH}.count_trial_cohort_members", return_value=None), \
             patch(f"{_AUTH}.get_user_id", return_value=None), \
             patch(f"{_AUTH}.send_pin_email") as send, \
             patch(f"{_AUTH}.create_pin_for_email") as create_pin:
            resp = api_client.post(INIT, json={"email": "D@Example.com"})
        assert resp.status_code == 200
        assert resp.json()["detail"] == {"waitlist": True, "email": "d@example.com"}
        send.assert_not_called()
        create_pin.assert_not_called()


class TestThePinRequest:
    def test_a_full_cohort_sends_no_pin_email(self, api_client):
        with patch(_PHASE, "P0"), \
             patch(f"{_AUTH}.count_trial_cohort_members", return_value=25), \
             patch(f"{_AUTH}.get_user_id", return_value=None), \
             patch(f"{_AUTH}.send_pin_email") as send, \
             patch(f"{_AUTH}.create_pin_for_email") as create_pin:
            resp = api_client.post(INIT, json={"email": "full@example.com"})
        assert resp.json()["detail"]["waitlist"] is True
        send.assert_not_called()
        create_pin.assert_not_called()

    def test_a_free_slot_sends_the_pin(self, api_client):
        with patch(_PHASE, "P0"), \
             patch(f"{_AUTH}.count_trial_cohort_members", return_value=24), \
             patch(f"{_AUTH}.get_user_id", return_value=None), \
             patch(f"{_AUTH}.generate_pin", return_value="123456"), \
             patch(f"{_AUTH}.hash_pin", return_value="h"), \
             patch(f"{_AUTH}.send_pin_email", return_value=(True, False)) as send, \
             patch(f"{_AUTH}.create_pin_for_email", return_value=True):
            resp = api_client.post(INIT, json={"email": "room@example.com"})
        detail = resp.json()["detail"]
        assert detail["bypass"] is False
        assert "waitlist" not in detail
        assert send.call_count == 2  # the bypass probe, then the real send

    def test_an_existing_account_signs_in_when_the_cohort_is_full(self, api_client):
        with patch(_PHASE, "P0"), \
             patch(f"{_AUTH}.count_trial_cohort_members", return_value=999) as count, \
             patch(f"{_AUTH}.get_user_id", return_value=7), \
             patch(f"{_AUTH}.generate_pin", return_value="123456"), \
             patch(f"{_AUTH}.hash_pin", return_value="h"), \
             patch(f"{_AUTH}.send_pin_email", return_value=(True, False)), \
             patch(f"{_AUTH}.create_pin_for_email", return_value=True):
            resp = api_client.post(INIT, json={"email": "member@example.com"})
        assert resp.json()["detail"]["bypass"] is False
        count.assert_not_called()

    def test_the_no_mail_bypass_is_held_to_the_same_cap(self, api_client, signed_in):
        db = _FakeCohortDb(members=25)
        with patch(_PHASE, "P0"), \
             patch(f"{_AUTH}.count_trial_cohort_members", return_value=24), \
             patch(f"{_USERS}._connection.get_db_connection", side_effect=db.connection), \
             patch(f"{_AUTH}.get_user_id", return_value=None), \
             patch(f"{_AUTH}.generate_pin", return_value="123456"), \
             patch(f"{_AUTH}.hash_pin", return_value="h"), \
             patch(f"{_AUTH}.send_pin_email", return_value=(True, True)), \
             patch(f"{_AUTH}.add_user_by_email") as add_user, \
             patch(f"{_AUTH}.create_session") as create_session:
            # The lock-free preview saw a slot; the locked count says it went in the meantime.
            resp = api_client.post(INIT, json={"email": "race@example.com"})
        assert resp.json()["detail"]["waitlist"] is True
        add_user.assert_not_called()
        create_session.assert_not_called()


class TestNoOtherPhaseIsAffected:
    @pytest.mark.parametrize("phase", ["P1", "P2", "p1"])
    def test_the_counter_is_never_read(self, api_client, signed_in, phase):
        with patch(_PHASE, phase), \
             patch(f"{_AUTH}.count_trial_cohort_members") as count, \
             patch(f"{_AUTH}.trial_cohort_slot") as slot, \
             patch(f"{_AUTH}.hash_pin", return_value="h"), \
             patch(f"{_AUTH}.verify_pin_for_email", return_value=True), \
             patch(f"{_AUTH}.get_user_id", return_value=None), \
             patch(f"{_AUTH}.add_user_by_email", return_value=501) as add_user, \
             patch(f"{_AUTH}.create_session", return_value="sess-p1"):
            resp = api_client.post(VERIFY, json={"email": "open@example.com", "pin": "123456"})
        assert resp.json()["detail"]["session_token"] == "sess-p1"
        add_user.assert_called_once_with("open@example.com")
        count.assert_not_called()
        slot.assert_not_called()

    @pytest.mark.parametrize("phase", ["P1", "P2"])
    def test_the_pin_request_is_never_gated(self, api_client, phase):
        with patch(_PHASE, phase), \
             patch(f"{_AUTH}.count_trial_cohort_members", return_value=None) as count, \
             patch(f"{_AUTH}.get_user_id", return_value=None), \
             patch(f"{_AUTH}.generate_pin", return_value="123456"), \
             patch(f"{_AUTH}.hash_pin", return_value="h"), \
             patch(f"{_AUTH}.send_pin_email", return_value=(True, False)), \
             patch(f"{_AUTH}.create_pin_for_email", return_value=True):
            resp = api_client.post(INIT, json={"email": "open@example.com"})
        assert resp.json()["detail"]["bypass"] is False
        count.assert_not_called()

    def test_an_unrecognised_phase_keeps_the_cap_on(self, api_client):
        """`current_launch_phase` falls back to P0, so a typo never opens signup."""
        with patch(_PHASE, "GA"), \
             patch(f"{_AUTH}.count_trial_cohort_members", return_value=25), \
             patch(f"{_AUTH}.get_user_id", return_value=None), \
             patch(f"{_AUTH}.send_pin_email") as send:
            resp = api_client.post(INIT, json={"email": "typo@example.com"})
        assert resp.json()["detail"]["waitlist"] is True
        send.assert_not_called()


class TestTheJoinTheListForm:
    def test_an_address_joins_the_list_and_nothing_is_sent(self, api_client):
        with patch(_PHASE, "P0"), \
             patch(f"{_AUTH}.check_waitlist_join", return_value=MagicMock(allowed=True)), \
             patch(f"{_AUTH}.add_to_trial_waitlist", return_value=True) as add, \
             patch(f"{_AUTH}.send_pin_email") as send:
            resp = api_client.post(WAITLIST, json={"email": "  Wait@Example.com "})
        assert resp.status_code == 200
        assert resp.json()["detail"] == {"joined": True}
        add.assert_called_once_with("wait@example.com", "P0")
        send.assert_not_called()

    @pytest.mark.parametrize("email", ["", "   ", "not-an-email", "a@b", "x" * 250 + "@example.com"])
    def test_a_malformed_address_is_400(self, api_client, email):
        with patch(f"{_AUTH}.add_to_trial_waitlist") as add:
            resp = api_client.post(WAITLIST, json={"email": email})
        assert resp.status_code == 400
        add.assert_not_called()

    def test_a_database_fault_is_503_not_a_silent_success(self, api_client):
        with patch(f"{_AUTH}.check_waitlist_join", return_value=MagicMock(allowed=True)), \
             patch(f"{_AUTH}.add_to_trial_waitlist", return_value=False):
            resp = api_client.post(WAITLIST, json={"email": "w@example.com"})
        assert resp.status_code == 503

    def test_rate_limited_is_429_with_retry_after(self, api_client):
        blocked = MagicMock(allowed=False, retry_after_seconds=120)
        with patch(f"{_AUTH}.check_waitlist_join", return_value=blocked), \
             patch(f"{_AUTH}.add_to_trial_waitlist") as add:
            resp = api_client.post(WAITLIST, json={"email": "w@example.com"})
        assert resp.status_code == 429
        assert resp.headers["retry-after"] == "120"
        add.assert_not_called()

    def test_the_form_takes_no_field_but_the_email(self):
        from cqc_lem.api.routers.auth import WaitlistJoinRequest

        assert set(WaitlistJoinRequest.model_fields) == {"email"}


class TestTheRepository:
    def test_cap_zero_never_opens_a_slot(self):
        from cqc_lem.platform.db.repositories.users import trial_cohort_slot

        db = _FakeCohortDb(members=0)
        with patch(f"{_USERS}._connection.get_db_connection", side_effect=db.connection):
            with trial_cohort_slot(0) as has_room:
                assert has_room is False

    def test_the_lock_is_released_when_the_body_raises(self):
        from cqc_lem.platform.db.repositories.users import trial_cohort_slot

        db = _FakeCohortDb(members=0)
        with patch(f"{_USERS}._connection.get_db_connection", side_effect=db.connection):
            with pytest.raises(RuntimeError):
                with trial_cohort_slot(25) as has_room:
                    assert has_room is True
                    raise RuntimeError("insert blew up")
        assert any("RELEASE_LOCK" in s for s in db.statements)
        assert db.closed == 1

    def test_count_reads_the_number(self):
        from cqc_lem.platform.db.repositories.users import count_trial_cohort_members

        db = _FakeCohortDb(members=7)
        with patch(f"{_USERS}._connection.get_db_connection", side_effect=db.connection):
            assert count_trial_cohort_members() == 7
        assert "is_admin = 0" in db.statements[0]
        assert "trial_started_at IS NOT NULL" in db.statements[0]

    def test_count_is_none_not_zero_on_a_fault(self):
        from cqc_lem.platform.db.repositories.users import count_trial_cohort_members

        db = _FakeCohortDb(count_error=mysql.connector.Error("down"))
        with patch(f"{_USERS}._connection.get_db_connection", side_effect=db.connection):
            assert count_trial_cohort_members() is None

    def test_waitlist_insert_is_idempotent_sql(self):
        from cqc_lem.platform.db.repositories.users import add_to_trial_waitlist

        db = _FakeCohortDb()
        with patch(f"{_USERS}._connection.get_db_connection", side_effect=db.connection):
            assert add_to_trial_waitlist("w@example.com", "P0") is True
        assert "INSERT INTO trial_waitlist" in db.statements[0]
        assert "ON DUPLICATE KEY UPDATE" in db.statements[0]

    def test_waitlist_insert_fault_is_false(self):
        from cqc_lem.platform.db.repositories.users import add_to_trial_waitlist

        with patch(f"{_USERS}._connection.get_db_connection",
                   side_effect=mysql.connector.Error("down")):
            assert add_to_trial_waitlist("w@example.com", "P0") is False

    def test_the_facade_re_exports_the_three_names(self):
        from cqc_lem.utilities import db

        for name in ("count_trial_cohort_members", "trial_cohort_slot", "add_to_trial_waitlist"):
            assert name in db.__all__
            assert callable(getattr(db, name))

