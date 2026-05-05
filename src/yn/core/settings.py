from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "localhost"
    postgres_db: str = "yukinoise"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}/{self.postgres_db}"
    
    app_host: str = "localhost"
    app_port: int = 8000
    app_workers: int = 4
    
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()