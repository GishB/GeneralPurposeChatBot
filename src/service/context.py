import pytz
from service.base import Singleton
from service.config import APP_CONFIG, Secrets
from service.logger import ContextVarsContainer, LoggerConfigurator


class AppContext(metaclass=Singleton):

    @property
    def logger(self):
        return self._logger_manager.async_logger

    def __init__(self, secrets: Secrets):
        self.timezone = pytz.timezone(secrets.app.timezone)
        self.context_vars_container = ContextVarsContainer()
        self._logger_manager = LoggerConfigurator(
            log_lvl=secrets.log.log_lvl,
            log_file_path=secrets.log.log_file_abs_path,
            metric_file_path=secrets.log.metric_file_abs_path,
            audit_file_path=secrets.log.audit_file_abs_path,
            audit_host_ip=secrets.log.audit_host_ip,
            audit_host_uid=secrets.log.audit_host_uid,
            context_vars_container=self.context_vars_container,
            timezone=self.timezone,
            rotation=secrets.log.log_rotation,
        )
        self.logger.info("App context initialized.")

    def get_logger(self):
        return self.logger

    def get_context_vars_container(self):
        return self.context_vars_container

    def get_pytz_timezone(self):
        return self.timezone

    async def on_startup(self):
        self.logger.info("Application is starting up.")
        # self._check_gigachat_connection()
        self.logger.info("All connections checked. Application is up and ready.")

    async def on_shutdown(self):
        self.logger.info("Application is shutting down.")
        self._logger_manager.remove_logger_handlers()


APP_CTX = AppContext(APP_CONFIG)


__all__ = [
    "APP_CTX",
]
