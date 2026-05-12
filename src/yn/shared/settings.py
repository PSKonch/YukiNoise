from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "127.0.0.1"
    postgres_db: str = "yukinoise"

    @property
    def postgres_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}/{self.postgres_db}"

    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_workers: int = 4

    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    refresh_token_expire_minutes: int = 60 * 24 * 30  # 30 days
    secret_key: str = (
        "your-secret-key"  # Change this to a secure random key in production
    )
    algorithm: str = "HS256"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
