import asyncio
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from service.logger import LoggerConfigurator
from service.config import PostgreSettings

class PostgresClient:
    def __init__(
            self,
            config: PostgreSettings,
            logger: LoggerConfigurator
        ):
        self.settings = config
        self.logger = logger

        self._pool:  AsyncPostgresSaver | None = None
        self._lock = asyncio.Lock()

        self.logger.info(f"Initializing Postgres client... {id(self)}")
        self._log_config_info()

    def _log_config_info(self) -> None:
        """ Show config information for Postgres """
        password = self.settings.password
        password_len = len(password) if password else None

        if not password_len or password_len == 0:
            self.logger.warning(f"Password not defined!")
        else:
            prefix = password[:2] if password_len >= 2 else ""
            suffix = password[-2:] if password_len >= 2 else ""
            masked = f"{prefix}**{suffix}" if password_len >= 4 else "***"
            self.logger.info(f"Password defined: {masked}")

        self.logger.info(
            f"user={self.settings.postgres_user}"
            f"host={self.settings.postgres_host}"
            f"port={self.settings.postgres_port}"
            f"dbname={self.settings.postgres_db}"
        )
        self.logger.info(
            f"poll_min_size={self.settings.poll_min_size}"
            f"poll_max_size={self.settings.poll_max_size}"
            f"poll_max_idle={self.settings.poll_max_idle:.1f}s"
        )

    async def ensure_pool(self) -> None:
        """ Ensure Postgres pool is initialized

        Notes:
            Create on startup. Pull must be alive all the app timeline.

        Raises:
            psycopg.OperationalError if no connection is available;
            asyncio.TimeoutError if no connection is available in short time;
        """
        if self._pool is None:
            async with self._lock:
                if self._pool is None:
                    self.logger.info(f"Postgres.ensure_pool: Creating new Postgres pool...")
                    self._pool = AsyncConnectionPool(
                        conninfo=self.config.conninfo,
                        min_size=self.config.pool_min_size,
                        max_size=self.config.pool_max_size,
                        max_idle=self.config.pool_max_idle
                    )
                    await self._pool.open(wait=True)
                    stats = self._pool.get_stats()
                    self.logger.info(f"Postgres.ensure_pool: Pool created. Pool size={stats.get('pool_size', 0)}")

    async def _take_conn_in_loop(self, dead_connection_count: int, max_attempts: int) -> AsyncConnection | None:
        while dead_connection_count < max_attempts:
            conn = await self._pool.getconn()
            try:
                await conn.execute("SELECT 1")
                self.logger.debug(f"Alive conn {id(conn)} retrived after {dead_connection_count} dead connections")
                await conn.execute("ROLLBACK")
                break

            except Exception as connection_error:
                dead_connection_count += 1
                self.logger.warning(
                    f"Dead connection {id(conn)} retrived."
                    f" Attempt number {dead_connection_count}/{max_attempts}: {connection_error}"
                )
                await conn.close()
                conn = None
        return conn

    async def get_user_checkpointer(self):
        self.logger.debug(f"Postgres.get_user_checkpointer: {id(self)}")
        await self.ensure_pool()

        conn = await self._take_conn_in_loop(
            dead_connection_count=0,
            max_attempts=self.settings.pool_max_size
        )

        if conn is None:
            self.logger.critical(
                f"Critical error in get_user_checkpointer()."
                f" All the {self.settings.pool_max_size} connections are dead."
            )

        await conn.set_autocommit(True)

        try:
            yield AsyncPostgresSaver(conn)
        finally:
            await self._pool.putconn(conn)
            self.logger.debug(f"Postgres.get_user_checkpointer: conn {id(conn)} returned to the pool {id(self)}")

    async def get_pool_stats(self) -> dict[str, Any] | None:
        if self._pool is None:
            self.logger.debug("Postgres.get_pool_stats not initialized")
            return None
        stats = self._pool.get_stats()
        self.logger.info(
            f"Postgres.get_pool_stats: {id(self): pool_size={stats.get('pool_size', 0)}}"
            f"pool_available={stats.get('pool_available', 0)}"
            f"request_waiting={stats.get('request_waiting', 0)}"
        )
        return stats

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
            self.logger.info(f"Postgres.close Singleton poll closed {id(self)}")
        else:
            self.logger.debug(f"Postgres.close already closed {id(self)}")

    def health_check(self) -> bool:
        return self._pool is not None
