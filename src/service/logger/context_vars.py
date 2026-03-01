from contextvars import ContextVar

from .models import ContextLog


class ContextVarsContainer:
    @property
    def context_vars(self) -> ContextLog:
        return ContextLog(
            rqUId=self.x_trace_id_var.get(),
            rqTime=self.x_request_time_var.get(),
            systemId=self.x_client_id_var.get(),
            gwSessionId=self.x_aigw_session_id_var.get(),
            userId=self.x_user_id_var.get(),
        )

    def __init__(self):
        self.x_trace_id_var = ContextVar("rquid", default=None)
        self.x_request_time_var = ContextVar("rqtm", default=None)
        self.x_client_id_var = ContextVar("systemId", default=None)
        self.x_aigw_session_id_var = ContextVar("gwSessionId", default=None)
        self.x_user_id_var = ContextVar("userId", default=None)

    def set_context_vars(
        self,
        x_trace_id: str = None,
        x_request_time: str = None,
        x_client_id: str = None,
        x_aigw_session_id: str = None,
        x_user_id: str = None,
        **kwargs,
    ):
        self.x_trace_id_var.set(x_trace_id)
        self.x_request_time_var.set(x_request_time)
        self.x_client_id_var.set(x_client_id)
        self.x_aigw_session_id_var.set(x_aigw_session_id)
        self.x_user_id_var.set(x_user_id)

    def get_context_vars(self):
        return (
            self.x_trace_id_var.get(),
            self.x_request_time_var.get(),
            self.x_client_id_var.get(),
            self.x_aigw_session_id_var.get(),
            self.x_user_id_var.get(),
        )


__all__ = ["ContextVarsContainer"]
