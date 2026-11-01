"""Fixtures shared by every scenario plus a tiny pytest plugin that writes the
per-scenario outcomes to a JSON file (--results-json=PATH)."""
import json
import time
from pathlib import Path

import pytest

from .api import Api
from .cache import Cache
from .config import settings
from .db import Db
from .events import StatusEvents
from .stack import down, service_logs, up, wait_healthy, wait_until


# ---------------------------------------------------------------- plugin ----

def pytest_addoption(parser):
    parser.addoption("--results-json", default=None,
                     help="write per-scenario outcomes to this file")


def pytest_configure(config):
    config._grader_outcomes = {}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    marker = item.get_closest_marker("scenario")
    if marker is None:
        return
    sid = marker.args[0]
    store = item.config._grader_outcomes
    if report.when == "setup" and report.failed:
        store[sid] = {"scenario": sid, "passed": False, "duration_s": report.duration,
                      "detail": "setup failed: " + _short(report.longreprtext)}
    elif report.when == "call":
        store[sid] = {"scenario": sid, "passed": report.passed, "duration_s": report.duration,
                      "detail": "" if report.passed else _short(report.longreprtext)}


def pytest_sessionfinish(session, exitstatus):
    path = session.config.getoption("--results-json")
    if not path:
        return
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(list(session.config._grader_outcomes.values()), indent=2))


def _short(text: str, limit: int = 2000) -> str:
    return text if len(text) <= limit else text[-limit:]


# -------------------------------------------------------------- fixtures ----

@pytest.fixture(scope="session")
def stack():
    api = Api(settings.base_url)
    if settings.manage_stack:
        up(settings.compose_dir)
    wait_healthy(api)
    yield api
    if settings.manage_stack:
        logs_dir = Path("results") / "last-run"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "order-service.log").write_text(service_logs(settings.compose_dir, tail=2000))
        down(settings.compose_dir)


@pytest.fixture(scope="session")
def db():
    d = Db(settings.pg_dsn)
    yield d
    d.close()


@pytest.fixture(scope="session")
def cache():
    c = Cache(settings.redis_url)
    yield c
    c.close()


@pytest.fixture(scope="session")
def events():
    e = StatusEvents(settings.kafka_bootstrap, settings.status_topic)
    yield e
    e.close()


@pytest.fixture
def api(stack, db, cache):
    """Fresh state for every scenario."""
    db.reset()
    cache.reset()
    return stack


class Consumer:
    """Helpers for waiting on the Kafka consumer without sleeping blind."""

    def __init__(self, api: Api, db: Db, events: StatusEvents):
        self.api = api
        self.db = db
        self.events = events

    def wait_for_history(self, order_id: str, sequence: int,
                         timeout_s: float | None = None) -> bool:
        """True once an applied event with this sequence shows in history.
        History is never cached, so this is the honest 'consumer caught up'."""
        timeout = timeout_s or settings.consumer_timeout_s
        return wait_until(lambda: sequence in self.db.history_sequences(order_id), timeout, 0.1)

    def barrier(self, order_id: str | None = None) -> str:
        """Everything produced before this call has been consumed when it returns.

        Works because the topic has one partition and the listener has
        concurrency 1: a canary event on a throwaway order is only applied
        after everything ahead of it. Returns the canary order id."""
        canary = order_id or self.api.create_ok()["id"]
        self.events.send(canary, "PAID", 1, source="grader-barrier")
        assert self.wait_for_history(canary, 1), "barrier canary was never consumed"
        return canary


@pytest.fixture
def consumer(api, db, events):
    return Consumer(api, db, events)


@pytest.fixture
def clock():
    return time.monotonic
