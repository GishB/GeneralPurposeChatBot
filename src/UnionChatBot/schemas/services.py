from pydantic import BaseModel
from pydantic import Field


class ChatRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=4,
        max_length=500,
        examples=[
            "Я ваСя ПупкИН! Привет! Мне нравится работать. Как долго действует коллективный договор на предприятии?"
        ],
    )
    user_id: str = Field(..., examples=["0", "123124214"])
    request_id: str = Field(..., examples=["a1b2c3d4e5f67890"])
    source_name: str = Field(..., examples=["telegram", "www.profkom-nevazot.ru"])

    class Config:
        extra = "forbid"


class ChatResponse(BaseModel):
    response: str = Field(..., examples=["Привет Вася Пупкин! Долго действует!"])
    request_id: str = Field(..., examples=["a1b2c3d4e5f67890"])
    status: str = Field(..., examples=["success", "failed"])
    user_id: str = Field(..., examples=["0", "123124214"])

    class Config:
        extra = "forbid"
