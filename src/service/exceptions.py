from fastapi import status


class AgentError(Exception):
    """
    Базовый класс для ошибок агента
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR


class AgentInternalError(AgentError):
    r"""
    Внутренние баги графа\логики
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
