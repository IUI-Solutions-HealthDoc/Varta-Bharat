from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]

# The value shipped in .env.example. Fine for local development, never anywhere else.
EXAMPLE_JWT_SECRET = "local-only-development-secret-change-this-before-deployment-123456789"
MIN_JWT_SECRET_BYTES = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
    )

    environment: str = "local"

    database_url: str = "postgresql://varta:varta@localhost:5432/varta"
    # Owner login used only by Alembic migrations; falls back to database_url.
    alembic_database_url: str | None = None
    valkey_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "varta-media"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    jwt_issuer: str = "varta-api"
    jwt_audience: str = "varta-client"

    @model_validator(mode="after")
    def _strong_secret_outside_local(self) -> "Settings":
        if self.environment != "local":
            if len(self.jwt_secret.encode()) < MIN_JWT_SECRET_BYTES:
                raise ValueError(
                    f"JWT_SECRET must be at least {MIN_JWT_SECRET_BYTES} bytes "
                    "outside ENVIRONMENT=local"
                )
            if self.jwt_secret == EXAMPLE_JWT_SECRET:
                raise ValueError("JWT_SECRET is still the .env.example value; set a unique secret")
        return self


settings = Settings()
