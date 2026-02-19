"""
Здесь можно разместить функции, не связанные с бизнес-логикой, например, нормализация ответов, обогащение данных и т.д.
"""

import uuid
from datetime import datetime

from fastapi import Header

from service.context import APP_CTX


# pylint: disable=C0103
def common_headers(
    header_x_trace_id: str = Header(
        ...,
        alias="x-trace-id",
        description="Уникальный идентификатор экземпляра процесса (основной операции).",
        example=uuid.uuid4(),
    ),
    header_x_request_time: str = Header(
        ...,
        alias="x-request-time",
        description="Время отправки запроса в формате ISO 8601.",
        example=str(datetime.now(tz=APP_CTX.get_pytz_timezone()).isoformat()),
    ),
    header_x_source_id: str = Header(
        ...,
        alias="x-source-name",
        description="Уникальное название системы которая отправляет запрос.",
        example="telegram",
    ),
    header_x_user_id: str = Header(
        ...,
        alias="x-user-id",
        description="ID пользователя",
        example=uuid.uuid4(),
    ),
) -> dict:
    return {
        "x-trace-id": header_x_trace_id,
        "x-request-time": header_x_request_time,
        "x-source-id": header_x_source_id,
        "x-user-id": header_x_user_id,
    }
