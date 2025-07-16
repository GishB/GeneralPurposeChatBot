from UnionChatBot.utils.ChatHistoryManager import ChatHistoryManager
from UnionChatBot.utils.ChromaAdapter import ChromaAdapter
from UnionChatBot.utils.EmbeddingAPI import MyEmbeddingFunction
from UnionChatBot.utils.RedisAdapters import SemanticRedisCache
from UnionChatBot.utils.YandexModelAPI import MyYandexModel


def setting_up(
    folder_id: str,
    api_key: str,
    embeding_api: str,
    model_name: str = "yandexgpt",
    host_vector_db: str = "localhost",
    port_vector_db: int = 32000,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    similarity_threshold: float = 0.95,
    topk_documents: int = 4,
    max_history_length: int = 5,
    **kwargs,
) -> MyYandexModel:
    """Setting up new session for all services.

    Notes:
        Redis, Yandex GPT API, ChromaDB are included.

    """
    embedding_function = MyEmbeddingFunction(
        api_url=embeding_api, folder_id=folder_id, iam_token=api_key, text_type="query"
    )

    semantic_cache = SemanticRedisCache(
        host=redis_host,
        port=redis_port,
        db=0,
        similarity_threshold=similarity_threshold,
    )

    chroma_adapter = ChromaAdapter(
        host=host_vector_db,
        port=port_vector_db,
        topk_documents=topk_documents,
        api_key=api_key,
        folder_id=folder_id,
        text_type="query",
    )

    chat_manager = ChatHistoryManager(
        redis_host=redis_host,
        redis_port=redis_port,
        redis_db=1,
        max_history_length=max_history_length,
    )
    return MyYandexModel(
        folder_id=folder_id,
        api_key=api_key,
        model_name=model_name,
        embedding_function=embedding_function,
        redis_cache=semantic_cache,
        chroma_adapter=chroma_adapter,
        chat_manager=chat_manager,
    )


def get_prompt(path_to_prompts: str = "./prompts") -> str:
    with open(
        f"{path_to_prompts}/WorkerUnionDefault.txt", "r", encoding="utf-8"
    ) as file:
        text_content = file.read()
    return text_content
