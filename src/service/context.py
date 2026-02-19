import pytz
from langchain_community.embeddings.yandex import YandexGPTEmbeddings
from langchain_openai import ChatOpenAI

from service.base import Singleton
from service.config import APP_CONFIG, Secrets
from service.logger import ContextVarsContainer, LoggerConfigurator
from modules.langfuse_ext import LangfuseClient
from modules.chroma_ext import ChromaAdapter
from modules.redis_ext import RedisAdapter
from modules.postgres_ext import PostgresClient
from agents.profkom_consultant import UnionAgent

class AppContext(metaclass=Singleton):
    @property
    def profkom_agent(self):
        return UnionAgent(
                   logger=self.logger,
                   llms=\
                       {
                           "default": ChatOpenAI(**self.get_yandexgpt_base_params())
                       },
                   cache=self.redis_ext,
                   langfuse_client=self.langfuse_ext.client,
                   chroma_client=self.chroma_ext,
                   )

    @property
    def postgres_ext(self):
        return PostgresClient (
                logger=self.logger,
                config=self._postgres_base_params
        )

    @property
    def logger(self):
        return self._logger_manager.async_logger

    @property
    def langfuse_ext(self):
        return LangfuseClient\
                (
                app_config=self._langfuse_base_params,
                logger=self.logger,
                )

    @property
    def chroma_ext(self):
        return ChromaAdapter \
            (
            logger=self.logger,
            similarity_filter= self._chroma_base_params.similarity_filter_score,
            **{
                "API_KEY":  self._chroma_base_params.openai_api_key,
                "FOLDER_ID":  self._chroma_base_params.openai_folder_id,
                "CHROMA_MAX_RAG_DOCUMENTS": self._chroma_base_params.chroma_max_rag_documents}
            )

    @property
    def yandexgpt_embeddings_client(self):
        return YandexGPTEmbeddings \
            (
                folder_id=self._yandexgpt_base_params.openai_folder_id,
                iam_token=self._yandexgpt_base_params.openai_api_key
            )

    @property
    def redis_ext(self):
        return RedisAdapter\
            (
             logger = self.logger,
             embeddings = self.yandexgpt_embeddings_client,
             redis_url = self._redis_base_params.redis_url,
             redis_threshold = self._redis_base_params.redis_threshold,
             redis_ttl = self._redis_base_params.redis_ttl
             )

    @property
    def postgres_ext(self):
        return PostgresClient\
            (
            logger=self.logger,
            )

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
        self._langfuse_base_params = secrets.langfuse
        self._postgres_base_params = secrets.postgres
        self._chroma_base_params = secrets.chroma
        self._yandexgpt_base_params = secrets.llm
        self._redis_base_params = secrets.redis


        self._langfuse_client: LangfuseClient | None = None
        self._chroma_client: ChromaAdapter | None = None
        self._yandexgpt_embeddings: YandexGPTEmbeddings | None = None
        self._redis_ext: RedisAdapter | None = None
        self._postgres_ext: PostgresClient | None = None
        self._profkom_agent: UnionAgent | None = None

        self.logger.info("App context initialized.")
        self.logger.info(f"{self.__class__.__name__}")
        self.logger.info(f"Timezone is {self.timezone}")

    def get_logger(self) -> LoggerConfigurator:
        return self.logger

    async def get_langfuse(self) -> LangfuseClient:
        if not self._langfuse_client:
            self._langfuse_client = self.langfuse_ext
        await self._langfuse_client.on_startup()
        return self._langfuse_client

    async def get_chroma(self) -> ChromaAdapter:
        if not self._chroma_client:
            self._chroma_client = self.chroma_ext
        return self._chroma_client

    async def get_redis(self) -> RedisAdapter:
        if not self._redis_ext:
            self._redis_ext = self.redis_ext
        return self._redis_ext

    async def get_yandexgpt_embeddings(self):
        if not self._yandexgpt_embeddings:
            self._yandexgpt_embeddings = self.yandexgpt_embeddings_client
        return self._yandexgpt_embeddings

    def get_agent(self) -> UnionAgent:
        """ Simple get for Agent Graph.

        Returns:
            Compiled Agent Graph.
        """
        if not self._profkom_agent:
            self._profkom_agent = self.profkom_agent
        return self._profkom_agent

    def get_postgres_client(self) -> PostgresClient:
        if not self._postgres_ext:
            self._postgres_ext = self.postgres_ext
        return self._postgres_ext

    def get_yandexgpt_base_params(self):
        return self._yandexgpt_base_params.base_params

    def get_context_vars_container(self):
        return self.context_vars_container

    def get_pytz_timezone(self):
        return self.timezone

    async def on_startup(self):
        self.logger.info("Application is starting up.")
        await self.get_langfuse()
        self.logger.info(f"Langfuse is healthy {self.langfuse_ext.health_check()}")
        await self.get_chroma()
        self.logger.info(f"Chroma is healthy {self.chroma_ext.health_check()}")
        await self.get_redis()
        self.logger.info(f"Redis is healthy {self.redis_ext.health_check()}")

        # self.get_postgres_client()
        self.get_agent()
        await self.get_yandexgpt_embeddings()
        self.logger.info("All connections checked. Application is up and ready.")

    async def on_shutdown(self):
        self.logger.info("Application is shutting down.")
        self._logger_manager.remove_logger_handlers()


APP_CTX = AppContext(APP_CONFIG)


__all__ = [
    "APP_CTX",
]
