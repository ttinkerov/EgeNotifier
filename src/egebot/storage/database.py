from __future__ import annotations

import sys
from pathlib import Path

import asyncpg
from loguru import logger

from egebot.config import Settings

_SCHEMA = Path(__file__).with_name("schema.sql")


class DatabaseError(RuntimeError):
    pass


class Database:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._dsn = settings.dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self._pool is not None:
            return

        logger.info(
            "Connecting to PostgreSQL at {}:{}/{}…",
            self._settings.db_addr,
            self._settings.db_port,
            self._settings.db_name,
        )

        await self._ensure_database_exists()

        try:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
        except (OSError, asyncpg.PostgresError) as exc:
            raise DatabaseError(self._hint(exc)) from exc

        try:
            await self._ensure_schema()
        except asyncpg.PostgresError as exc:
            await self.disconnect()
            raise DatabaseError(f"Не удалось создать таблицы: {exc}") from exc

        logger.info("Database ready")

    async def _ensure_database_exists(self) -> None:
        conn = await asyncpg.connect(self._settings.admin_dsn)
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                self._settings.db_name,
            )
            if not exists:
                logger.info('Creating database "{}"…', self._settings.db_name)
                await conn.execute(
                    f'CREATE DATABASE "{self._settings.db_name}" ENCODING \'UTF8\''
                )
        finally:
            await conn.close()

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def _ensure_schema(self) -> None:
        sql = _SCHEMA.read_text(encoding="utf-8")
        async with self.pool.acquire() as conn:
            await conn.execute(sql)
            await conn.execute(
                """
                ALTER TABLE tg_accounts
                ADD COLUMN IF NOT EXISTS spoiler_scores BOOLEAN NOT NULL DEFAULT FALSE
                """
            )

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database is not connected")
        return self._pool

    @staticmethod
    def _hint(exc: BaseException) -> str:
        base = (
            f"Не удалось подключиться к PostgreSQL.\n"
            f"Проверь DB_USER, DB_PASS, DB_ADDR, DB_PORT в .env.\n"
            f"Ошибка: {exc}"
        )
        if sys.platform == "win32":
            base += (
                "\n\nWindows: запусти PostgreSQL-службу и убедись, что пароль "
                "пользователя postgres верный."
            )
        return base
