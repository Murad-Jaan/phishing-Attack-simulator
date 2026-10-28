from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = "development"
    APP_ENV: str = "development"
    APP_BASE_URL: str = "http://127.0.0.1:3000"
    API_BASE_URL: str = "http://127.0.0.1:8000"

    SESSION_SECRET: str = "changeme-session-secret-min-32-chars"
    CSRF_SECRET: str = "changeme-csrf-secret-min-32-chars"

    DATABASE_URL: str = "postgresql+psycopg://phish:phishpass@postgres:5432/phishsim"
    REDIS_URL: str = "redis://redis:6379/0"
    TEST_DATABASE_URL: str = (
        "postgresql+psycopg://phish:phishpass@postgres:5432/phishsim_test"
    )
    TEST_REDIS_URL: str = "redis://redis:6379/15"

    SMTP_HOST: str = "mailpit"
    SMTP_PORT: int = 1025
    SMTP_FROM: str = "sandbox@example.test"
    ALLOWED_SEND_DOMAINS: str = "example.com,*.test,*.invalid"

    RETENTION_DAYS: int = 90
    REPORTING_MIN_GROUP: int = 5

    SESSION_IDLE_MINUTES: int = 60
    SESSION_ABSOLUTE_HOURS: int = 8
    CSRF_TOKEN_TTL_SECONDS: int = 600
    LOGIN_CSRF_TOKEN_TTL_SECONDS: int = 300
    RATE_LIMIT_ACCOUNT_WINDOW_SECONDS: int = 900
    RATE_LIMIT_IP_WINDOW_SECONDS: int = 900
    RATE_LIMIT_LOCKOUT_BASE_SECONDS: int = 900
    RATE_LIMIT_LOCKOUT_MAX_SECONDS: int = 3600
    TRUSTED_PROXY_NETWORKS: str = ""
    TRUSTED_PROXY_ALLOW_LOOPBACK: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_allowed_domains(self) -> List[str]:
        return [d.strip() for d in self.ALLOWED_SEND_DOMAINS.split(",") if d.strip()]

    def validate_secrets(self) -> None:
        if self.ENV == "production" or self.APP_ENV == "production":
            if self.SESSION_SECRET.startswith("changeme") or len(self.SESSION_SECRET) < 32:
                raise RuntimeError("SESSION_SECRET must be set in production")
            if self.CSRF_SECRET.startswith("changeme") or len(self.CSRF_SECRET) < 32:
                raise RuntimeError("CSRF_SECRET must be set in production")


settings = Settings()
