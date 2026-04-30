"""
Утилиты для оценки качества профсоюзного консультанта.
"""

from .agent_client import (
    AgentRequest,
    AgentResponse,
    AgentConnectionError,
    call_agent_chat,
    call_agent,
    health_check,
)
from .dataset import (
    load_golden_dataset,
    create_test_case_from_scenario,
    auto_annotate_scenario,
)
from .kimi_judge import KimiJudgeModel
from .judge_factory import get_judge_model
from .metrics import (
    get_metric,
    create_answer_relevancy_metric,
    create_recommendation_quality_metric,
    create_response_structure_metric,
    create_response_completeness_metric,
    create_hallucination_rate_metric,
    create_toxicity_rate_metric,
    create_empathy_friendly_metric,
)

__all__ = [
    # Agent client
    "AgentRequest",
    "AgentResponse",
    "AgentConnectionError",
    "call_agent_chat",
    "call_agent",
    "health_check",
    # Dataset
    "load_golden_dataset",
    "create_test_case_from_scenario",
    "auto_annotate_scenario",
    # Judge model
    "get_judge_model",
    "KimiJudgeModel",
    # Metrics
    "get_metric",
    "create_answer_relevancy_metric",
    "create_recommendation_quality_metric",
    "create_response_structure_metric",
    "create_response_completeness_metric",
    "create_hallucination_rate_metric",
    "create_toxicity_rate_metric",
    "create_empathy_friendly_metric",
]
