import os
from logging import DEBUG, INFO

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

load_dotenv("../../.env")


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

    host: str = Field(validation_alias="APP_HOST", default="0.0.0.0")
    port: int = Field(validation_alias="APP_PORT", default=8080)
    name: str = Field(validation_alias="PROJECT_NAME", default="KarlMarksAlive")
    timezone: str = Field(validation_alias="TIMEZONE", default="Europe/Moscow")
    stage: str = Field(validation_alias="STAGE", default="dev")


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
    audit_host_uid: str = Field(validation_alias="HOST_UID", default="42bd6cbe-126b-41bf-a65c-9ce19450901ccd")

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
    Настройки YandexGPTFoundation models.
    """

    model_name: str = Field(validation_alias="MODEL_NAME", default="yandexgpt")
    temperature: float = Field(validation_alias="TEMPERATURE", default=0.1)
    # profanity_check: bool = Field(validation_alias="PROFANCIE_CHECK", default=False)

    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY", default=None)
    openai_folder_id: str = Field(validation_alias="OPENAI_FOLDER_ID", default=None)
    openai_api_base: str = Field(validation_alias="OPENAI_API_BASE", default="https://llm.api.cloud.yandex.net/v1")

    @property
    def model(self):
        return f"gpt://{self.openai_folder_id}/{self.model_name}"

    @property
    def base_params(self):
        return \
            {
                "model": self.model,
                "temperature": self.temperature,
                "openai_api_key": self.openai_api_key,
                "openai_api_base": self.openai_api_base,
            }


class LangFuseSettings(BaseAppSettings):
    """
    Настройка для логирования.
    """

    secret_key: str = Field(validation_alias="LANGFUSE_SECRET_KEY", default="")
    public_key: str = Field(validation_alias="LANGFUSE_PUBLIC_KEY", default="")
    host: str = Field(validation_alias="LANGFUSE_HOST", default="http://127.0.0.1:3000")
    stage: str = Field(validation_alias="LANGFUSE_STAGE", default="dev")


class ChromaSettings(BaseAppSettings):
    """
    Для работы с векторной базой данных.
    """

    similarity_filter_score: float = Field(validation_alias="SIMILARITY_FILTER", default=1.5)
    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY", default=None)
    openai_folder_id: str = Field(validation_alias="OPENAI_FOLDER_ID", default=None)
    chroma_max_rag_documents: int = Field(validation_alias="CHROMA_MAX_RAG_DOCUMENTS", default=42)
    collection_name: str = Field(validation_alias="COLLECTION_NAME", default="PRODUCTION_PROFKOM")
    embeding_api: str = Field(
        validation_alias="EMBEDDING_API",
        default="https://llm.api.cloud.yandex.net:443/foundationModels/v1/textEmbedding",
    )
    time_sleep: float = Field(validation_alias="TIME_SLEEP_RATE_EMBEDDER", default=0.01)

    @property
    def header(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api_key}",
            "x-folder-id": self.folder_id,
        }

    @property
    def doc_model_uri(self):
        return f"emb://{self.folder_id}/text-search-doc/latest"

    @property
    def query_model_uri(self):
        return f"emb://{self.folder_id}/text-search-query/latest"

class PostgreSettings(BaseAppSettings):
    user: str = Field(validation_alias="PG_USER", default="postgres")
    password: str = Field(validation_alias="PG_PASSWORD", default="")
    postgres_db: str = Field(validation_alias="POSTGRES_DB", default="postgres")
    schema: str = Field(validation_alias="PG_SCHEMA", default="postgres")
    host: str = Field(validation_alias="PG_HOST", default="localhost")
    port: int = Field(validation_alias="PG_PORT", default=5432)

    sslmode: str = Field(validation_alias="PG_SSLMODE", default="disable")
    pool_min_size: int = Field(validation_alias="POOL_MIN_SIZE", default=5)
    pool_max_size: int = Field(validation_alias="POOL_MAX_SIZE", default=20)
    pool_max_idle: int = Field(validation_alias="POOL_MAXIDLE", default=60)
    keepalive_interval: int = Field(validation_alias="KEEPALIVE_INTERVAL", default=60)
    keepalive_count: int = Field(validation_alias="KEEPALIVE_COUNT", default=5)

    @property
    def encoded_pass(self) -> str:
        from urllib.parse import quote_plus
        return quote_plus(self.password)

    @property
    def conninfo(self) -> str:
        return (
            f"postgresql://{self.user}:{self.encoded_pass}"
            f"@{self.host}:{self.port}/{self.postgres_db}"
            f"?sslmode={self.sslmode}"
            f"&options=-c%20search_path%3D{self.schema}"
            f"&keepalives=1"
            f"&keepalives_idle={self.pool_max_idle}"
            f"&keepalives_interval={self.keepalive_interval}"
            f"&keepalives_count={self.keepalive_count}"
        )


class RedisSettings(BaseAppSettings):
    redis_url: str = Field(validation_alias="REDIS_URL", default="redis://127.0.0.1:6379")
    redis_threshold: float = Field(validation_alias="REDIS_THRESHOLD", default=0.05)
    redis_ttl: int = Field(validation_alias="REDIS_TTL", default=3600)


class Secrets:
    """
    Класс, агрегирующий все настройки приложения.
    """

    app: AppSettings = AppSettings()
    llm: YandexGPTSettings = YandexGPTSettings()
    postgres: PostgreSettings = PostgreSettings()
    log: LogSettings = LogSettings()
    chroma: ChromaSettings = ChromaSettings()
    langfuse: LangFuseSettings = LangFuseSettings()
    redis: RedisSettings = RedisSettings()


APP_CONFIG = Secrets()

__all__ = [
    "Secrets",
    "APP_CONFIG",
]
