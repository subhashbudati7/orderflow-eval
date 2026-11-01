"""Where the stack lives. Everything is overridable from the environment so the
same scenarios run against compose on a laptop or against a pre-started stack
in CI."""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_DIR = ROOT / "environment"


@dataclass(frozen=True)
class Settings:
    base_url: str = os.environ.get("GRADER_BASE_URL", "http://localhost:58080")
    kafka_bootstrap: str = os.environ.get("GRADER_KAFKA", "localhost:59094")
    status_topic: str = os.environ.get("GRADER_STATUS_TOPIC", "order.status-updates")
    pg_dsn: str = os.environ.get(
        "GRADER_PG_DSN",
        "postgresql://orderflow:orderflow@localhost:55432/orderflow",
    )
    redis_url: str = os.environ.get("GRADER_REDIS_URL", "redis://localhost:56379/0")
    # How long we give the consumer to catch up before calling a scenario failed.
    consumer_timeout_s: float = float(os.environ.get("GRADER_CONSUMER_TIMEOUT", "15"))
    # API.md promises the cache reflects a change "within a couple of seconds".
    cache_visibility_s: float = float(os.environ.get("GRADER_CACHE_VISIBILITY", "5"))
    # 1 = grader runs docker compose up/down itself. 0 = assume it's already running.
    manage_stack: bool = os.environ.get("GRADER_MANAGE_STACK", "1") == "1"
    compose_dir: Path = Path(os.environ.get("GRADER_COMPOSE_DIR", str(ENVIRONMENT_DIR)))
    concurrency: int = int(os.environ.get("GRADER_CONCURRENCY", "24"))


settings = Settings()
