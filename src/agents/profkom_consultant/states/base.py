from typing import List, TypedDict
from .status import AgentStatus

class AgentState(TypedDict, total=False):
    user_id: str
    user_history: List[str]
    model_answers: List[str]

    text: str
    is_valid: bool
    validation_errors: List[str]
    answers: List[str]
    parts: List[str]
    final_answer: str
    additional_documents: List[str]
    additional_info: str

    # loop-контроля
    status: AgentStatus
    counter_loop: int
