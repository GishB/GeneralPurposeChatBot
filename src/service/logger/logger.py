import json
import sys
from dataclasses import asdict
from logging import DEBUG
from time import time

import pytz
from loguru import logger as loguru_logger

from service.base import Singleton

from .context_vars import ContextVarsContainer
from .models import ContextLog, Event, EventParam, Log, Metric, dataclass_as_json_str
from .utils import mask_sensitive_data


class LoggerWrapper:
    def __init__(self, audit_uid_pod, audit_ip_address):
        self.logger = None
        self.audit_uid_pod = audit_uid_pod
        self.audit_ip_address = audit_ip_address

    def patch(self, *args, **kwargs):
        self.logger = loguru_logger.patch(*args, **kwargs)
        return self

    def metric(self, metric_name, metric_value):
        self.logger.info(
            "<metric>",
            metric_name=metric_name,
            metric_value=metric_value,
            target="metric",
        )

    def audit(self, event_name, event_params):
        self.logger.info(
            "<audit-event>",
            audit_event_name=event_name,
            audit_uid_pod=self.audit_uid_pod,
            audit_ip_address=self.audit_ip_address,
            audit_params=event_params,
            target="audit-event",
        )

    def __getattr__(self, name):
        return getattr(self.logger, name)


class LoguruPatcher:
    def __init__(self, context_vars_container: ContextVarsContainer, timezone: pytz.timezone, full_message_print: bool):
        self.context_vars_container = context_vars_container
        self.timezone: pytz.timezone = timezone
        self.full_message_print: bool = full_message_print

    @staticmethod
    def format_stdout_record(record) -> str:
        base_record = "<level>{level: <7}</level> | <green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        base_msg = "{name} | {message}\n"

        if record["extra"].get("rqUId") is not None:
            return base_record + "{extra[rqUId]} | " + base_msg
        return base_record + base_msg

    def patching(self, record: dict):
        _context_log: ContextLog = self.context_vars_container.context_vars
        _time_iso = record["time"].replace(tzinfo=self.timezone).isoformat()
        _target = record["extra"].get("target")

        if _target == "metric":
            _log_record = Metric(
                rqUId=_context_log.rqUId,
                metric_name=record["extra"].get("metric_name", "unknown"),
                metric_value=record["extra"].get("metric_value", 1),
            )
        elif _target == "audit-event":
            _log_record = Event(
                name=record["extra"].get("audit_event_name", None),
                createdAt=int(time()*1000),
                params=[
                    EventParam(name="uid-pod", value=record["extra"].get("audit_uid_pod")),
                    EventParam(name="ip-address", value=record["extra"].get("audit_ip_address")),
                    EventParam(name="request-Id", value=_context_log.rqUId),
                    EventParam(name="request-Time", value=_context_log.rqTime),
                    EventParam(name="params", value=record["extra"].get("audit_params")),
                ],
            )
        else:
            record["extra"].update({"target": "log"})
            args = record["extra"].get("args", None)
            if args:
                message = args.get("message", {})
                if self.full_message_print:
                    print(json.dumps(message, indent=4, ensure_ascii=False))
                message = mask_sensitive_data(
                    message, message_type=record["extra"].get("message_type"), path=record["extra"].get("path")
                )
                args.update({"message": str(message), "headers": str(args["headers"])})

            _log_record = Log(
                levelName=str(record["level"].name),
                asctime=_time_iso,
                moduleName=str(record["name"]),
                funcName=str(record["function"]),
                message=str(record["message"]),
                stackTrace=record["extra"].get("exception", None),
                rqUId=_context_log.rqUId,
                rqTime=_context_log.rqTime,
                systemId=_context_log.systemId,
                gwSessionId=_context_log.gwSessionId,
                userId=_context_log.userId,
                args=args,
            )

        record["extra"]["serialized"] = dataclass_as_json_str(_log_record)
        record["extra"].update(asdict(_context_log))


class LoggerConfigurator(metaclass=Singleton):
    # pylint: disable=R0902
    @property
    def async_logger(self):
        return self.logger

    def __init__(
        # pylint: disable=R0917
        self,
        log_lvl: int,
        log_file_path: str,
        metric_file_path: str,
        audit_file_path: str,
        audit_host_ip: str,
        audit_host_uid: str,
        context_vars_container: ContextVarsContainer,
        timezone: pytz.timezone,
        rotation: str = "10 MB",
    ):
        self.handlers: dict = {0: "standard-loguru"}
        self.log_lvl: int = log_lvl
        self.log_file_path: str = log_file_path
        self.metric_file_path: str = metric_file_path
        self.audit_file_path: str = audit_file_path
        self.audit_host_ip: str = audit_host_ip
        self.audit_host_uid: str = audit_host_uid
        self.rotation: str = rotation

        full_message_print = log_lvl == DEBUG
        _patcher = LoguruPatcher(context_vars_container, timezone, full_message_print)
        self._init_async_logger(_patcher)

    def add_handler(self, *args, handler_name="", **kwargs):
        self.handlers[self.logger.add(*args, **kwargs)] = handler_name

    def list_logger_handlers(self):
        print(f"Displaying active handlers ({len(self.handlers)}):")
        for handler_id, handler_name in self.handlers.items():
            print(f" -- Handler id: {handler_id} | Status: ready | Handler name: {handler_name}")

    def _init_async_logger(self, loguru_patcher: LoguruPatcher):
        print("Setting up logging handlers")
        self.list_logger_handlers()
        self.delete_handler_by_id(0)
        self.logger = LoggerWrapper(audit_uid_pod=self.audit_host_uid, audit_ip_address=self.audit_host_ip).patch(
            loguru_patcher.patching
        )

        self.add_handler(
            handler_name="log-file-handler",
            sink=self.log_file_path,
            serialize=False,
            format="{extra[serialized]}",
            rotation=self.rotation,
            retention=0,
            compression=None,
            level=self.log_lvl,
            enqueue=True,
            filter=lambda record: record["extra"].get("target") == "log",
        )

        self.add_handler(
            handler_name="metric-file-handler",
            sink=self.metric_file_path,
            serialize=False,
            format="{extra[serialized]}",
            rotation=self.rotation,
            retention=0,
            compression=None,
            enqueue=True,
            filter=lambda record: record["extra"].get("target") == "metric",
        )

        self.add_handler(
            handler_name="audit-file-handler",
            sink=self.audit_file_path,
            serialize=False,
            format="{extra[serialized]}",
            rotation=self.rotation,
            retention=0,
            compression=None,
            enqueue=True,
            filter=lambda record: record["extra"].get("target") == "audit-event",
        )

        self.add_handler(
            handler_name="log-console-handler",
            sink=sys.stdout,
            level=self.log_lvl,
            format=loguru_patcher.format_stdout_record,
            filter=lambda record: record["extra"].get("target") == "log",
        )

        self.list_logger_handlers()
        print("---------------- All handlers are ready, now loguru is in charge ----------------")

    def delete_handler_by_id(self, handler_id):
        handler_name = self.handlers.get(handler_id, "<None>")
        try:
            loguru_logger.remove(handler_id)
            self.handlers.pop(handler_id)
            print(f"Successfully removed {handler_name} logger with id {handler_id}")
        except ValueError:
            print(f"Failed to remove {handler_name} logger with id {handler_id}")

    def remove_logger_handlers(self):
        self.logger.info("Destroying logging handlers, loguru says goodbye")

        for handler_id in list(self.handlers):
            self.delete_handler_by_id(handler_id)

        self.list_logger_handlers()


__all__ = ["LoggerConfigurator"]
