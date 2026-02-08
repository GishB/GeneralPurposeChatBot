import json
from dataclasses import asdict, dataclass


@dataclass
class ContextLog:
    # pylint: disable=C0103,R0902
    rqUId: None | str
    rqTime: None | str
    systemId: None | str
    gwSessionId: None | str
    userId: None | str


@dataclass
class Log:
    # pylint: disable=C0103,R0902
    levelName: str
    asctime: str
    moduleName: str
    funcName: str
    message: str
    stackTrace: str | None
    rqUId: None | str
    rqTime: None | str
    systemId: None | str
    gwSessionId: None | str
    userId: None | str
    args: str | None


@dataclass
class Metric:
    # pylint: disable=C0103,R0902
    rqUId: str
    metric_name: str
    metric_value: int


@dataclass
class EventParam:
    # pylint: disable=C0103,R0902
    name: str
    value: str


@dataclass
class Event:
    # pylint: disable=C0103,R0902
    name: str
    createdAt: int
    params: list[EventParam]


def dataclass_as_json_str(dataclass_object) -> str:
    return json.dumps(asdict(dataclass_object), ensure_ascii=False)
