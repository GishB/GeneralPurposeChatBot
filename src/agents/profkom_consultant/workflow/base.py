from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.profkom_consultant import UnionAgent
from agents.profkom_consultant.states import AgentState, AgentStatus


def build_builder(agent: UnionAgent, checkpointer: MemorySaver | None) -> CompiledStateGraph:
    r"""Создаем граф профсоюзного агента

    Notes:
        1. Содержит ноду проверки информации на вход\выход согласно комплаенс политики;
        2. Может запустить цикл если ответ модели не отвечает на вопрос пользователя.

    Args:
        checkpointer: Объект для хранения состояния агента;
        agent: Экземпляр агента;

    Returns:
        Скомпилированный граф для работы агента.
    """
    builder = StateGraph(AgentState, is_async=True)
    builder.add_node("validate", agent.validate_text)
    builder.add_node("decompose_question", agent.decompose_question)
    builder.add_node("answer_parts_async", agent.answer_parts_async)
    builder.add_node("reject_stub", agent.reject_stub)
    builder.add_node("collect_final_answer", agent.collect_final_answer)
    builder.add_node("validate_final_answer", agent.validate_final_answer)
    builder.add_node("check_user_answer", agent.check_user_answer)
    builder.add_node("generate_additional_questions", agent.generate_additional_questions)
    builder.add_node("update_user_history_context", agent.update_user_history_context)

    builder.set_entry_point("validate")

    def route_in(state: AgentState):
        return "decompose_question" if state["is_valid"] else "reject_stub"

    def route_loop(state: AgentState):
        return (
            "generate_additional_questions"
            if state["status"] == AgentStatus.AGAIN
            else "validate_final_answer"
            if state["status"] == AgentStatus.DONE
            else END
        )

    def route_out(state: AgentState):
        return "update_user_history_context" if state["is_valid"] else "reject_stub"

    builder.add_conditional_edges(
        "validate", route_in, {"decompose_question": "decompose_question", "reject_stub": "reject_stub"}
    )

    builder.add_conditional_edges(
        "check_user_answer",
        route_loop,
        {
            "generate_additional_questions": "generate_additional_questions",
            "validate_final_answer": "validate_final_answer",
        },
    )

    builder.add_conditional_edges(
        "validate_final_answer",
        route_out,
        {"update_user_history_context": "update_user_history_context", "reject_stub": "reject_stub"},
    )

    builder.add_edge("reject_stub", "update_user_history_context")
    builder.add_edge("decompose_question", "answer_parts_async")
    builder.add_edge("answer_parts_async", "collect_final_answer")
    builder.add_edge("collect_final_answer", "check_user_answer")
    builder.add_edge("generate_additional_questions", "answer_parts_async")
    builder.add_edge("update_user_history_context", END)

    validation_agent = builder.compile(checkpointer=checkpointer)
    return validation_agent
