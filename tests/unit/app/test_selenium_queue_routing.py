"""Smoke tests: every Selenium-backed task must declare queue='selenium'.

If a task is dispatched without an explicit queue and task_routes hasn't been
applied (e.g. unit tests calling .apply_async directly), Celery falls back to
the queue embedded in the task object.  These tests confirm the queue attribute
is set so the task always lands in the right queue regardless of call-site.
"""

import pytest

pytestmark = pytest.mark.unit

SELENIUM_TASKS = [
    "automate_commenting",
    "automate_reply_commenting",
    "automate_appreciation_dms_for_user",
    "automate_profile_viewer_engagement",
    "engage_with_profile_viewer",
    "send_private_dm",
    "invite_to_connect",
    "update_stale_profile",
    "automate_invites_to_company_page_for_user",
]

NON_SELENIUM_TASKS = [
    "post_to_linkedin",
    "clean_stale_invites",
]


@pytest.mark.parametrize("task_name", SELENIUM_TASKS)
def test_selenium_task_routes_to_selenium_queue(task_name):
    """Each Selenium task must have queue='selenium' on its task object."""
    import importlib
    mod = importlib.import_module("cqc_lem.app.run_automation")
    task = getattr(mod, task_name)
    assert task.queue == "selenium", (
        f"{task_name}.queue is '{task.queue}', expected 'selenium'. "
        "Add queue='selenium' to its @shared_task.task() decorator."
    )


@pytest.mark.parametrize("task_name", NON_SELENIUM_TASKS)
def test_non_selenium_task_does_not_route_to_selenium_queue(task_name):
    """Non-Selenium tasks must NOT be routed to the selenium queue."""
    import importlib
    mod = importlib.import_module("cqc_lem.app.run_automation")
    task = getattr(mod, task_name)
    assert getattr(task, "queue", "celery") != "selenium", (
        f"{task_name} should stay on the default queue, not 'selenium'."
    )


def test_celeryconfig_declares_selenium_queue():
    """celeryconfig.py must declare the 'selenium' queue in task_queues."""
    from cqc_lem.app import celeryconfig
    queue_names = {q.name for q in celeryconfig.task_queues}
    assert "selenium" in queue_names, "task_queues must include a Queue named 'selenium'"
    assert "celery" in queue_names, "task_queues must include the default 'celery' queue"


def test_celeryconfig_task_routes_cover_all_selenium_tasks():
    """task_routes must include every known Selenium task."""
    from cqc_lem.app import celeryconfig
    routes = celeryconfig.task_routes
    for task_name in SELENIUM_TASKS:
        full_name = f"cqc_lem.app.run_automation.{task_name}"
        assert full_name in routes, f"{full_name} missing from task_routes"
        assert routes[full_name].get("queue") == "selenium", (
            f"{full_name} task_routes entry must map to queue='selenium'"
        )
