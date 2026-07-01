import os
from logging import DEBUG, INFO

from dotenv import find_dotenv, load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(find_dotenv())


class BaseAppSettings(BaseSettings):
    """
    Базовый класс для настроек.
    """

    model_config = SettingsConfigDict(populate_by_name=True)

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
    chat_max_generation_seconds: int = Field(
        validation_alias="CHAT_MAX_GENERATION_SECONDS", default=300
    )
    chat_job_ttl_seconds: int = Field(validation_alias="CHAT_JOB_TTL_SECONDS", default=900)
    chat_job_redis_db: int = Field(validation_alias="CHAT_JOB_REDIS_DB", default=3)


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


class LLMSettings(BaseAppSettings):
    """
    Настройки провайдера LLM (OpenRouter / DeepSeek / OpenAI-совместимые API).
    """

    model_name: str = Field(validation_alias="LLM_MODEL_NAME", default="deepseek/deepseek-chat")
    temperature: float = Field(validation_alias="LLM_TEMPERATURE", default=0.1)
    max_retries: int = Field(validation_alias="LLM_MAX_RETRIES", default=5)

    api_key: str = Field(validation_alias="LLM_API_KEY", default="")
    api_base: str = Field(validation_alias="LLM_API_BASE", default="https://openrouter.ai/api/v1")

    openrouter_referer: str = Field(validation_alias="OPENROUTER_REFERER", default="")
    openrouter_title: str = Field(validation_alias="OPENROUTER_TITLE", default="UnionChatBot")
    openrouter_provider_order: str = Field(validation_alias="OPENROUTER_PROVIDER_ORDER", default="")
    openrouter_allow_fallbacks: bool = Field(validation_alias="OPENROUTER_ALLOW_FALLBACKS", default=True)

    fallback_llm_model_name: str = Field(validation_alias="FALLBACK_LLM_MODEL_NAME", default="yandexgpt")
    fallback_llm_api_base: str = Field(
        validation_alias="FALLBACK_LLM_API_BASE", default="https://llm.api.cloud.yandex.net/v1"
    )

    @model_validator(mode="before")
    @classmethod
    def _fallback_to_openai_env(cls, data):
        """Поддержка старых переменных OPENAI_* для обратной совместимости."""
        if isinstance(data, dict):
            if not data.get("LLM_API_KEY") and not data.get("api_key"):
                data["LLM_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
            if not data.get("LLM_API_BASE") and not data.get("api_base"):
                data["LLM_API_BASE"] = os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
            if not data.get("LLM_MODEL_NAME") and not data.get("model_name"):
                data["LLM_MODEL_NAME"] = os.getenv("MODEL_NAME", "deepseek/deepseek-chat")
        return data

    reasoning_effort: str = Field(validation_alias="LLM_REASONING_EFFORT", default="none")
    reasoning_effort_summary_critique: str = Field(
        validation_alias="LLM_REASONING_EFFORT_SUMMARY_CRITIQUE", default="low"
    )

    validation_model_name: str = Field(
        validation_alias="LLM_VALIDATION_MODEL_NAME", default="deepseek/deepseek-v4-flash"
    )
    validation_reasoning_effort: str = Field(
        validation_alias="LLM_VALIDATION_REASONING_EFFORT", default="none"
    )

    summary_model_name: str = Field(
        validation_alias="LLM_SUMMARY_MODEL_NAME", default="deepseek/deepseek-v4-pro"
    )
    summary_reasoning_effort: str = Field(
        validation_alias="LLM_SUMMARY_REASONING_EFFORT", default="low"
    )

    critic_model_name: str = Field(
        validation_alias="LLM_CRITIC_MODEL_NAME", default="deepseek/deepseek-v4-pro"
    )
    critic_reasoning_effort: str = Field(
        validation_alias="LLM_CRITIC_REASONING_EFFORT", default="low"
    )

    @staticmethod
    def _reasoning_extra_body(effort: str) -> dict | None:
        """OpenRouter `reasoning` для заданного уровня усилий.

        Args:
            effort: "none"/"off" — выключить reasoning; "minimal"/"low"/"medium"/"high" —
                задать бюджет; "" — оставить дефолт модели.

        Returns:
            extra_body для ChatOpenAI или None, если параметр слать не нужно.
        """
        effort = (effort or "").strip().lower()
        if not effort:
            return None
        if effort in ("none", "off", "disabled", "false"):
            return {"reasoning": {"enabled": False}}
        return {"reasoning": {"effort": effort}}

    @property
    def openrouter_extra_body(self) -> dict | None:
        """Дополнительное тело запроса для OpenRouter.

        Включает провайдер-роутинг и отключение reasoning.
        """
        extra: dict[str, Any] = {}
        if self.openrouter_provider_order:
            extra["provider"] = {
                "order": [p.strip() for p in self.openrouter_provider_order.split(",") if p.strip()],
                "allow_fallbacks": self.openrouter_allow_fallbacks,
            }
        reasoning = self._reasoning_extra_body(self.reasoning_effort)
        if reasoning:
            extra.update(reasoning)
        return extra if extra else None

    @property
    def openrouter_extra_body_no_provider(self) -> dict | None:
        """extra_body без провайдер-роутинга — для моделей с дефолтным провайдером."""
        return self._reasoning_extra_body(self.reasoning_effort)

    def base_params_with_reasoning(self, effort: str) -> dict:
        """base_params с заданным уровнем reasoning (только для primary/OpenRouter)."""
        params = {
            "model": self.model_name,
            "temperature": self.temperature,
            "openai_api_key": self.api_key,
            "openai_api_base": self.api_base,
            "max_retries": self.max_retries,
        }
        extra_body = self.openrouter_extra_body
        if extra_body is not None:
            params["extra_body"] = extra_body
        headers = {}
        if self.openrouter_referer:
            headers["HTTP-Referer"] = self.openrouter_referer
        if self.openrouter_title:
            headers["X-Title"] = self.openrouter_title
        if headers:
            params["default_headers"] = headers
        return params

    @property
    def base_params(self):
        """Параметры primary-LLM по умолчанию (reasoning отключён)."""
        return self.base_params_with_reasoning(self.reasoning_effort)

    @property
    def reasoning_node_params(self):
        """Параметры primary-LLM для нод summary/критики (reasoning low)."""
        return self.base_params_with_reasoning(self.reasoning_effort_summary_critique)

    @property
    def validation_params(self):
        """Параметры LLM для нод валидации (быстрая/cheap модель, reasoning off)."""
        params = {
            "model": self.validation_model_name,
            "temperature": self.temperature,
            "openai_api_key": self.api_key,
            "openai_api_base": self.api_base,
            "max_retries": self.max_retries,
        }
        extra_body = self.openrouter_extra_body_no_provider
        if extra_body is not None:
            params["extra_body"] = extra_body
        headers = {}
        if self.openrouter_referer:
            headers["HTTP-Referer"] = self.openrouter_referer
        if self.openrouter_title:
            headers["X-Title"] = self.openrouter_title
        if headers:
            params["default_headers"] = headers
        return params

    @property
    def summary_params(self):
        """Параметры LLM для ноды суммаризации (собственная модель, без провайдер-роутинга).

        Note:
            extra_body берётся из `_reasoning_extra_body`, поэтому НЕ содержит
            `provider.order` — это обязательно, иначе провайдеры из прод-конфига не
            обслуживают модель суммаризации и запрос падает с 404.
        """
        params = {
            "model": self.summary_model_name,
            "temperature": self.temperature,
            "openai_api_key": self.api_key,
            "openai_api_base": self.api_base,
            "max_retries": self.max_retries,
        }
        extra_body = self._reasoning_extra_body(self.summary_reasoning_effort)
        if extra_body is not None:
            params["extra_body"] = extra_body
        headers = {}
        if self.openrouter_referer:
            headers["HTTP-Referer"] = self.openrouter_referer
        if self.openrouter_title:
            headers["X-Title"] = self.openrouter_title
        if headers:
            params["default_headers"] = headers
        return params

    @property
    def critic_params(self):
        """Параметры LLM для ноды критики (check_user_answer, собственная модель, без провайдер-роутинга).

        Note:
            extra_body берётся из `_reasoning_extra_body`, поэтому НЕ содержит
            `provider.order` — это обязательно, иначе провайдеры из прод-конфига не
            обслуживают модель критики и запрос падает с 404.
        """
        params = {
            "model": self.critic_model_name,
            "temperature": self.temperature,
            "openai_api_key": self.api_key,
            "openai_api_base": self.api_base,
            "max_retries": self.max_retries,
        }
        extra_body = self._reasoning_extra_body(self.critic_reasoning_effort)
        if extra_body is not None:
            params["extra_body"] = extra_body
        headers = {}
        if self.openrouter_referer:
            headers["HTTP-Referer"] = self.openrouter_referer
        if self.openrouter_title:
            headers["X-Title"] = self.openrouter_title
        if headers:
            params["default_headers"] = headers
        return params

    @property
    def fallback_params(self):
        if not self.fallback_llm_api_base or not self.fallback_llm_model_name:
            return None
        return {
            "model": self.fallback_llm_model_name,
            "temperature": self.temperature,
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "openai_api_base": self.fallback_llm_api_base,
            "max_retries": self.max_retries,
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

    host: str = Field(validation_alias="CHROMA_HOST", default="127.0.0.1")
    port: int = Field(validation_alias="CHROMA_PORT", default=443)
    similarity_filter_score: float = Field(validation_alias="SIMILARITY_FILTER", default=1.5)
    openai_api_key: str = Field(validation_alias="OPENAI_API_KEY", default="")
    openai_folder_id: str = Field(validation_alias="OPENAI_FOLDER_ID", default="")
    chroma_max_rag_documents: int = Field(validation_alias="CHROMA_MAX_RAG_DOCUMENTS", default=42)
    collection_name: str = Field(validation_alias="COLLECTION_NAME", default="PRODUCTION_PROFKOM")
    embeding_api: str = Field(
        validation_alias="EMBEDDING_API",
        default="https://llm.api.cloud.yandex.net:443/foundationModels/v1/textEmbedding",
    )
    time_sleep: float = Field(validation_alias="TIME_SLEEP_RATE_EMBEDDER", default=0.1)
    max_retries: int = Field(validation_alias="CHROMA_MAX_RETRIES", default=5)
    request_timeout: float = Field(validation_alias="CHROMA_REQUEST_TIMEOUT", default=1)
    batch_size: int = Field(validation_alias="CHROMA_BATCH_SIZE", default=16)
    sleep_between_batches: int = Field(validation_alias="CHROMA_SLEEP_BETWEEN_BATCHES", default=2)

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

    history_limit: int = Field(validation_alias="HISTORY_LIMIT", default=10)

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
    port: int = Field(validation_alias="REDIS_PORT", default=6379)
    host: str = Field(validation_alias="REDIS_HOST", default="127.0.0.1")
    password: str = Field(validation_alias="REDIS_PASSWORD", default="")

    redis_threshold: float = Field(validation_alias="REDIS_THRESHOLD", default=0.05)
    redis_ttl: int = Field(validation_alias="REDIS_TTL", default=3600)

    user_counter_limit: int = Field(validation_alias="USER_COUNTER_LIMIT", default=10)
    user_ttl_limit: int = Field(validation_alias="USER_TTL_LIMIT", default=84000)
    rate_limit_template: str = Field(validation_alias="RATE_LIMIT_TEMPLATE", default="msg_count:{user_id}")

    @property
    def redis_url(self):
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}"
        return f"redis://{self.host}:{self.port}"


class Secrets:
    """
    Класс, агрегирующий все настройки приложения.
    """

    app: AppSettings = AppSettings()
    llm: LLMSettings = LLMSettings()
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
