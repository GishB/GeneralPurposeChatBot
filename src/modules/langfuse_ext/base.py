from langfuse import Langfuse
from langfuse.callback import CallbackHandler
from service.config import LangFuseSettings
from service.logger import LoggerConfigurator

class LangfuseClient:
    def __init__(self, app_config: LangFuseSettings, logger: LoggerConfigurator):
        self.config = app_config
        self.logger = logger

        self.logger.debug("Init LangfuseClient")
        self.logger.debug(f"{self.__class__.__name__}")
        self.logger.debug(f"Host: {self.config.host}")
        self.logger.debug(f"Secret Key: {self.config.secret_key[:4]}**{self.config.secret_key[-4:]}")
        self.logger.debug(f"Public Key: {self.config.public_key[:4]}**{self.config.public_key[-4:]}")
        self.logger.debug(f"Stage: {self.config.stage}")

        self.client = self.__create_client
        self.handler = self.__create_callback_handler

        self.logger.debug("LangFuse client created")

    @property
    def __create_client(self) -> Langfuse:
        """
        Create the LangFuse client object.
        """
        self.logger.debug("Create LangFuse client")
        return Langfuse(
            secret_key=self.config.secret_key,
            public_key=self.config.public_key,
            host=self.config.host,
        )

    @property
    def __create_callback_handler(self) -> CallbackHandler:
        """
        Create the callback handler.
        """
        return CallbackHandler(
            public_key=self.config.public_key,
            secret_key=self.config.secret_key,
            host=self.config.host,
            trace_name=self.config.stage,
        )

    def health_check(self) -> bool:
        """ Simple health check trigger.

        Return:
            True if connection exists.
        """
        is_healthy = self.client.auth_check()
        if not is_healthy:
            Warning("LangFuse Health check failed")
        return is_healthy
