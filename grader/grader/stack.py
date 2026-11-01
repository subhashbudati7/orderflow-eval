"""docker compose lifecycle and the small waiting helpers every scenario uses."""
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from .api import Api


class StackError(RuntimeError):
    pass


def compose(compose_dir: Path, *args: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    cmd = ["docker", "compose", *args]
    return subprocess.run(cmd, cwd=compose_dir, check=check, text=True,
                          capture_output=capture)


def up(compose_dir: Path, build: bool = True, timeout_s: float = 300) -> None:
    args = ["up", "-d", "--wait", "--wait-timeout", str(int(timeout_s))]
    if build:
        args.append("--build")
    try:
        compose(compose_dir, *args)
    except subprocess.CalledProcessError as e:
        logs = compose(compose_dir, "logs", "--no-color", "--tail", "200", "order-service",
                       check=False, capture=True).stdout
        raise StackError(f"stack did not come up: {e}\n--- order-service logs ---\n{logs}") from e


def down(compose_dir: Path) -> None:
    compose(compose_dir, "down", "-v", "--remove-orphans", check=False)


def service_logs(compose_dir: Path, tail: int = 400) -> str:
    return compose(compose_dir, "logs", "--no-color", "--tail", str(tail), "order-service",
                   check=False, capture=True).stdout


def wait_until(predicate: Callable[[], bool], timeout_s: float, interval_s: float = 0.2,
               what: str = "condition") -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval_s)
    return predicate()


def wait_healthy(api: Api, timeout_s: float = 120) -> None:
    if not wait_until(api.health, timeout_s, interval_s=1.0):
        raise StackError(f"{api.base_url} never reported healthy")
