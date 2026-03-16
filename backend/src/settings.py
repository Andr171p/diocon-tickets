from typing import Literal

from pathlib import Path

import pytz
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

TIMEZONE = "Asia/Yekaterinburg"
timezone = pytz.timezone(TIMEZONE)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)

TEMPLATES_DIR = BASE_DIR / "templates"

# Время истечения приглашения
INVITATION_EXPIRES_IN_DAYS = 7


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    host: str = "postgres"
    port: int = 5432
    user: str = "<USER>"
    password: str = "<PASSWORD>"
    db: str = "<DB>"
    driver: Literal["asyncpg"] = "asyncpg"

    @property
    def sqlalchemy_url(self) -> str:
        return f"postgresql+{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class MinIOSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MINIO_")

    access_key_id: str = "<ACCESS_KEY_ID>"
    secret_access_key: str = "<SECRET_ACCESS_KEY>"
    endpoint_url: str = "http://localhost:9900"


class JWTSettings(BaseSettings):
    access_token_expires_in_minutes: int = 30
    refresh_token_expires_in_days: int = 30


class MailSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MAIL_")

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_use_tls: bool = True
    smtp_user: str = ""
    smtp_password: str = ""
    default_from_email: str = "diocon@mail.ru"
    support_email: str = "diocon.support@mail.ru"


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    host: str = "localhost"
    port: int = 6679

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")

    name: str = "ДИО-Консалт"
    port: int = 8000

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"


class AdminSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ADMIN_")

    email: str = "admin@admin.com"
    password: str = "admin"


class Settings(BaseSettings):
    secret_key: str = "<SECRET_KEY>"
    frontend_url: str = "http://localhost:3000"

    app: AppSettings = AppSettings()
    postgres: PostgresSettings = PostgresSettings()
    minio: MinIOSettings = MinIOSettings()
    jwt: JWTSettings = JWTSettings()
    mail: MailSettings = MailSettings()
    admin: AdminSettings = AdminSettings()


settings = Settings()
