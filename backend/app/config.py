import os


class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_VERSION: str = os.getenv("APP_VERSION", "v2.0.0")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis-service")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres-0.postgres-headless")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "visitdb")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres123")


settings = Settings()
