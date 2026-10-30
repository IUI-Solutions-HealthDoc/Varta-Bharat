from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
    )

    environment: str = "local"

    database_url: str = "postgresql://varta:varta@localhost:5432/varta"
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


settings = Settings()
