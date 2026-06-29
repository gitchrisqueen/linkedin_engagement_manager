"""Reproducible LinkedIn-login debug harness.

Drives the live selenium-chrome browser through the app's own driver so what you
inspect is exactly what runs in production (and what lemvnc shows). Use it whenever
LinkedIn changes its login DOM and the credential step starts timing out.

Run it inside the selenium worker (it reaches selenium-chrome:4444 over the compose
network):

    sudo docker cp tools/debug_linkedin_login.py celery_worker_selenium:/tmp/dbg.py
    sudo docker exec celery_worker_selenium python /tmp/dbg.py --inspect            # non-destructive
    sudo docker exec celery_worker_selenium python /tmp/dbg.py --login --user-id 1  # real submit

--inspect dumps the login page's input fields + a screenshot so you can confirm the
selectors used by login_to_linkedin still match. --login exercises the real
login_to_linkedin() end-to-end (set LINKEDIN_APPROVAL_WAIT_SECONDS to control how
long it waits for the mobile-app device approval).
"""

import argparse
import json
import time

from selenium.webdriver.common.by import By

from cqc_lem.utilities.db import get_cookies, get_user_password_pair_by_id
from cqc_lem.utilities.selenium_util import get_driver_wait_pair

LOGIN_URL = "https://www.linkedin.com/login"


def inspect(user_id: int, out: str) -> None:
    email, password = get_user_password_pair_by_id(user_id)
    # Log only whether a password exists — never anything derived from its value.
    has_password = bool(password)
    print(f"[creds] user_id={user_id} email={email!r} password_set={has_password}")
    cookies = get_cookies("https://www.linkedin.com", email) if email else None
    print(f"[cookies] count={len(cookies) if cookies else 0}")

    driver, _ = get_driver_wait_pair(headless=False, session_name="login-debug", user_id=user_id)
    try:
        driver.get(LOGIN_URL)
        time.sleep(3)
        print(f"[page] url={driver.current_url!r} title={driver.title!r}")
        for el in driver.find_elements(By.TAG_NAME, "input"):
            try:
                print("  input:", json.dumps({
                    "id": el.get_attribute("id"),
                    "type": el.get_attribute("type"),
                    "autocomplete": el.get_attribute("autocomplete"),
                    "displayed": el.is_displayed(),
                }, ensure_ascii=False))
            except Exception as e:  # noqa: BLE001
                print("  input: <err>", e)
        driver.save_screenshot(out)
        print(f"[screenshot] {out}")
    finally:
        driver.quit()


def attempt_login(user_id: int) -> None:
    from cqc_lem.utilities.linkedin.helper import login_to_linkedin
    email, password = get_user_password_pair_by_id(user_id)
    driver, wait = get_driver_wait_pair(headless=False, session_name="login-attempt", user_id=user_id)
    try:
        login_to_linkedin(driver, wait, email, password)
        print(f"[login] returned; url={driver.current_url}")
    except Exception as e:  # noqa: BLE001
        print(f"[login] raised: {e}")
        print(f"[login] final url={driver.current_url}")
    finally:
        driver.quit()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-id", type=int, default=1)
    ap.add_argument("--inspect", action="store_true", help="dump login DOM (non-destructive)")
    ap.add_argument("--login", action="store_true", help="run the real login_to_linkedin flow")
    ap.add_argument("--screenshot", default="/tmp/login_debug.png")
    args = ap.parse_args()

    if args.login:
        attempt_login(args.user_id)
    else:  # default: inspect
        inspect(args.user_id, args.screenshot)
