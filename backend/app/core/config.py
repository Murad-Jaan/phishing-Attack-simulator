from pydantic_settings import BaseSettings
from typing import List


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
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def get_allowed_domains(self) -> List[str]:
        return [d.strip() for d in self.ALLOWED_SEND_DOMAINS.split(",") if d.strip()]


settings = Settings()
