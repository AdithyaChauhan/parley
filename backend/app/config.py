from pathlib import Path

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


settings = Settings()
