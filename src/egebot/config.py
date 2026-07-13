from functools import lru_cache
from typing import Self
from urllib.parse import quote_plus, urlparse, unquote

from egebot.__version__ import __version__
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    tg_api_token: str = Field(alias="TG_API_TOKEN")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    db_name: str | None = Field(default=None, alias="DB_NAME")
    db_user: str | None = Field(default=None, alias="DB_USER")
    db_pass: str | None = Field(default=None, alias="DB_PASS")
    db_addr: str = Field(default="localhost", alias="DB_ADDR")
    db_port: int = Field(default=5432, alias="DB_PORT")
    admin_ids: list[int] = Field(default_factory=list, alias="ADMIN_CHAT_IDS")
    proxy_url: str | None = Field(alias="PROXY_URL", default=None)
    log_level: str = Field(alias="LOG_LEVEL", default="INFO")
    data_encryption_key: str | None = Field(default=None, alias="DATA_ENCRYPTION_KEY")

    app_version: str = __version__

    poll_cooldown_sec: float = 2.0
    watcher_tick_sec: float = 5.0
    watcher_backoff_sec: float = 30.0
    watcher_concurrency: int = 3
    watcher_jitter_sec: float = 1.5

    rustest_origin: str = "https://checkege.rustest.ru"
    rustest_ua: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _split_admins(cls, raw: str | list[int] | None) -> list[int]:
        if raw is None or raw == "":
            return []
        if isinstance(raw, list):
            return raw
        return [int(chunk.strip()) for chunk in str(raw).split(",") if chunk.strip()]

    @model_validator(mode="after")
    def _build_database_url(self) -> Self:
        if self.db_addr == "localhost":
            self.db_addr = "127.0.0.1"

        if self.database_url:
            self._hydrate_from_database_url()
            return self

        required = {
            "DB_NAME": self.db_name,
            "DB_USER": self.db_user,
            "DB_PASS": self.db_pass,
        }
        missing = [key for key, value in required.items() if not value]
        if missing:
            raise ValueError(
                "Укажи DATABASE_URL или заполни: " + ", ".join(missing)
            )

        user = quote_plus(self.db_user)  # type: ignore[arg-type]
        password = quote_plus(self.db_pass)  # type: ignore[arg-type]
        self.database_url = (
            f"postgresql://{user}:{password}@{self.db_addr}:{self.db_port}/{self.db_name}"
        )
        return self

    def _hydrate_from_database_url(self) -> None:
        """Fill db_* fields from DATABASE_URL when discrete vars are omitted."""
        assert self.database_url is not None
        parsed = urlparse(self.database_url)
        if not self.db_user and parsed.username:
            self.db_user = unquote(parsed.username)
        if not self.db_pass and parsed.password is not None:
            self.db_pass = unquote(parsed.password)
        if parsed.hostname:
            self.db_addr = "127.0.0.1" if parsed.hostname == "localhost" else parsed.hostname
        if parsed.port:
            self.db_port = parsed.port
        path_name = (parsed.path or "").lstrip("/")
        if path_name and not self.db_name:
            self.db_name = path_name.split("/")[0] or None

    @property
    def can_auto_create_database(self) -> bool:
        return bool(self.db_user and self.db_name)

    @property
    def admin_dsn(self) -> str:
        user = quote_plus(self.db_user or "")
        password = quote_plus(self.db_pass or "")
        return f"postgresql://{user}:{password}@{self.db_addr}:{self.db_port}/postgres"

    @property
    def dsn(self) -> str:
        assert self.database_url is not None
        return self.database_url

    @property
    def rustest_scores_endpoint(self) -> str:
        return f"{self.rustest_origin}/api/exam"

    @property
    def rustest_captcha_endpoint(self) -> str:
        return f"{self.rustest_origin}/api/captcha"

    @property
    def rustest_signin_endpoint(self) -> str:
        return f"{self.rustest_origin}/api/participant/login"

    @property
    def rustest_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Referer": f"{self.rustest_origin}/exams",
            "Origin": self.rustest_origin,
            "User-Agent": self.rustest_ua,
            "X-Requested-With": "XMLHttpRequest",
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
