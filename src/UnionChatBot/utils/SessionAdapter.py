from UnionChatBot.CoreLogic import CoreQueryProcessor
from UnionChatBot.utils.ChatHistoryManager import ChatHistoryManager
from UnionChatBot.utils.ChromaAdapter import ChromaAdapter
from UnionChatBot.utils.EmbeddingAPI import MyEmbeddingFunction
from UnionChatBot.utils.RedisAdapters import SemanticRedisCache


def setting_up(
    model_name: str = "yandexgpt",
    similarity_threshold: float = 0.95,
    **kwargs,
) -> CoreQueryProcessor:
    """Setting up new session for all services.

    Notes:
        Redis, Yandex GPT API, ChromaDB are included.

    """
    embedding_function = MyEmbeddingFunction(text_type="query")

    semantic_cache = SemanticRedisCache(
        db=0,
        similarity_threshold=similarity_threshold,
    )

    chroma_adapter = ChromaAdapter(
        text_type="query",
    )

    chat_manager = ChatHistoryManager(
        redis_db=1,
    )
    return CoreQueryProcessor(
        model_name=model_name,
        embedding_function=embedding_function,
        redis_cache=semantic_cache,
        chroma_adapter=chroma_adapter,
        chat_manager=chat_manager,
    )
