from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# The .env file lives in the repo root: config.py -> app -> backend -> root
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # extra="ignore": .env also holds the POSTGRES_* values for Docker,
    # which the app doesn't need.
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: str
    # The private key that signs access tokens. Anyone who has it can make
    # valid tokens, so it lives only in .env.
    jwt_secret: str
    # Where Redis lives: online status and last seen (D22).
    redis_url: str
    # Which backend copy this is, when several run at once (D23). Shown in
    # /api/health, so you can check which copy a window talks to.
    copy_name: str = "A"

    # Where RabbitMQ lives: notification jobs (D25).
    rabbitmq_url: str
    # How long a job waits before the worker looks at it, so a message read
    # live is skipped (D25). In milliseconds, so tests can use a few hundred.
    notify_wait_ms: int = 5_000
    # How long to wait before try 2, 3 and 4: 10 s, 1 min, 5 min. Each one is
    # a queue's timer, so changing one means deleting that queue first (D25).
    notify_retry_ms: list[int] = [10_000, 60_000, 300_000]
    # For demos and tests: every job fails its first N tries on purpose.
    # 2 shows retries working; 10 sends a job all the way to notify.failed.
    notify_fake_fail_times: int = 0

    # Which notifier the worker uses (D26): "log" writes one log line (tests,
    # CI), "webpush" sends real browser notifications.
    notifier: Literal["log", "webpush"] = "log"
    # The VAPID key pair that proves a push came from Parley (D26). Empty until
    # you make them: then /api/push/key answers 503, and the worker refuses to
    # start with notifier "webpush".
    vapid_private_key: str = ""
    vapid_public_key: str = ""
    # Who the push services can contact about our pushes: a mailto: address.
    vapid_subject: str = ""


settings = Settings()
