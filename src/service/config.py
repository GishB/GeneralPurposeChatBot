import ssl
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import os
from logging import DEBUG, INFO

from cryptography import x509
from cryptography.hazmat.primitives import serialization

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

load_dotenv()


class BaseAppSettings(BaseSettings):
    """
    Базовый класс для настроек.
    """

    local: bool = Field(validation_alias="LOCAL", default=False)
    debug: bool = Field(validation_alias="DEBUG", default=False)

    @property
    def protocol(self) -> str:
        return "https" if self.local else "http"


class AppSettings(BaseAppSettings):
    """
    Настройки приложения.
    """

    app_host: str = Field(validation_alias="APP_HOST", default="0.0.0.0")
    app_port: int = Field(validation_alias="APP_PORT", default=8080)
    kube_net_name: str = Field(validation_alias="PROJECT_NAME", default="WORKERUNION")
    timezone: str = Field(validation_alias="TIMEZONE", default="Europe/Moscow")


class LogSettings(BaseAppSettings):
    """
    Настройки логирования.
    """

    private_log_file_path: str = Field(validation_alias="LOG_PATH", default=os.getcwd())
    private_log_file_name: str = Field(validation_alias="LOG_FILE_NAME", default="app.log")
    log_rotation: str = Field(validation_alias="LOG_ROTATION", default="10 MB")
    private_metric_file_path: str = Field(validation_alias="METRIC_PATH", default=os.getcwd())
    private_metric_file_name: str = Field(validation_alias="METRIC_FILE_NAME", default="app-metric.log")
    private_audit_file_path: str = Field(validation_alias="AUDIT_LOG_PATH", default=os.getcwd())
    private_audit_file_name: str = Field(validation_alias="AUDIT_LOG_FILE_NAME", default="events.log")
    audit_host_ip: str = Field(validation_alias="HOST_IP", default="127.0.0.1")
    audit_host_uid: str = Field(validation_alias="HOST_UID", default="63bd6cbe-170b-49bf-a65c-3ce967398ccd")

    @field_validator(
        "private_log_file_path",
        "private_metric_file_path",
        "private_audit_file_path",
    )
    @classmethod
    def validate_path(cls, value):
        if not os.path.exists(value):
            raise ValueError(f"Path does not exist: {value}")
        if not os.path.isdir(value):
            raise ValueError(f"Path is not a directory: {value}")
        return value

    @staticmethod
    def get_file_abs_path(path_name: str, file_name: str) -> str:
        return os.path.join(path_name.strip(), file_name.lstrip("/").strip())

    @property
    def log_file_abs_path(self) -> str:
        return self.get_file_abs_path(self.private_log_file_path, self.private_log_file_name)

    @property
    def metric_file_abs_path(self) -> str:
        return self.get_file_abs_path(self.private_metric_file_path, self.private_metric_file_name)

    @property
    def audit_file_abs_path(self) -> str:
        return self.get_file_abs_path(self.private_audit_file_path, self.private_audit_file_name)

    @property
    def log_lvl(self) -> int:
        return DEBUG if self.debug else INFO


class YandexGPTSettings(BaseAppSettings):
    """
    Настройки GigaChat.
    """
    model_name: str = Field(validation_alias="MODEL_NAME", default="YandexGPT")
    temperature: float = Field(validation_alias="TEMPERATURE", default=0.1)
    profanity_check: bool = Field(validation_alias="PROFANCIE_CHECK", default=False)



class Secrets:
    """
    Класс, агрегирующий все настройки приложения.
    """

    app: AppSettings = AppSettings()
    llm: YandexGPTSettings = YandexGPTSettings()
    log: LogSettings = LogSettings()


APP_CONFIG = Secrets()

__all__ = [
    "Secrets",
    "APP_CONFIG",
]
