from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Ответ для ручки /health"""

    status: str = Field(default="running", description="Service health check", max_length=7)

    class Config:
        json_schema_extra = {"example": {"status": "running"}}


class InfoResponse(BaseModel):
    """Ответ для ручки /info"""

    name: str = Field(description="Service name", max_length=50)
    description: str = Field(description="Service description", max_length=200)
    type: str = Field(default="REST API", description="Service type", max_length=20)
    version: str = Field(description="Service version", max_length=20, pattern=r"^\d+.\d+.\d+")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "rest-template",
                "description": 'Python "Ai gateway" template for developing REST microservices',
                "type": "REST API",
                "version": "0.1.0",
            }
        }


class RateResponse(BaseModel):
    rating_result: str = Field(description="Rating that was recorded", max_length=50)
