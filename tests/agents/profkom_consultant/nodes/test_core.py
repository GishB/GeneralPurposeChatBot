from unittest.mock import MagicMock

from langchain_core.runnables import Runnable

from agents.profkom_consultant.nodes.core import UnionAgent


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeLLM(Runnable):
    """Мини-Runnable для проверки, какая LLM реально используется в цепочке."""

    def __init__(self, content):
        self._content = content
        self.called = False

    def invoke(self, input_value, config=None, **kwargs):
        self.called = True
        return FakeMessage(self._content)

    async def ainvoke(self, input_value, config=None, **kwargs):
        self.called = True
        return FakeMessage(self._content)


def _build_agent(llms: dict) -> UnionAgent:
    return UnionAgent(
        logger=MagicMock(),
        llms=llms,
        cache=MagicMock(),
        langfuse_client=MagicMock(),
        chroma_client=MagicMock(),
    )


class TestSummaryLLMWiring:
    def test_summary_role_is_exposed(self):
        sentinel = object()
        agent = _build_agent(
            {
                "default": object(),
                "reasoning": object(),
                "validation": object(),
                "summary": sentinel,
            }
        )

        assert agent.summary_llm is sentinel

    def test_summary_falls_back_to_reasoning(self):
        reasoning = object()
        agent = _build_agent({"default": object(), "reasoning": reasoning})

        assert agent.summary_llm is reasoning


class TestCollectFinalAnswerUsesSummaryLLM:
    async def test_collect_final_answer_invokes_summary_llm(self):
        summary_llm = FakeLLM("SUMMARY")
        reasoning_llm = FakeLLM("REASONING")
        agent = _build_agent(
            {
                "default": object(),
                "reasoning": reasoning_llm,
                "summary": summary_llm,
            }
        )

        agent.langfuse_client.get_prompt.return_value.get_langchain_prompt.return_value = (
            "Вопрос: {original_question}\nОтветы: {task_responses}"
        )

        state = {"text": "Как вступить в профсоюз?", "answers": ["Подать заявление."]}
        result = await agent.collect_final_answer(state)

        assert result["final_answer"] == "SUMMARY"
        assert summary_llm.called is True
        assert reasoning_llm.called is False
