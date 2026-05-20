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

    minio_endpoint: str = "127.0.0.1:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket: str = "tracks"

    rabbitmq_host: str = "127.0.0.1"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_managment_port: int = 15672

    @property
    def rabbitmq_url(self) -> str:
        return f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port}"

    @property
    def rabbitmq_management_url(self) -> str:
        return f"http://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_managment_port}"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
