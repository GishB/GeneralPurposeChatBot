from unittest.mock import MagicMock

import pytest

from agents.profkom_consultant.nodes.base import BaseAgentNodes


@pytest.fixture
def agent():
    instance = BaseAgentNodes.__new__(BaseAgentNodes)
    instance.HISTORY_LIMIT = 3
    return instance


class TestUpdateUserHistoryContext:
    def test_appends_question_and_answer(self, agent):
        state = {
            "text": "Новый вопрос",
            "final_answer": "Новый ответ",
        }

        result = agent.update_user_history_context(state)

        assert result["user_history"] == ["Новый вопрос"]
        assert result["model_answers"] == ["Новый ответ"]

    def test_trims_to_history_limit(self, agent):
        state = {
            "user_history": ["вопрос 1", "вопрос 2", "вопрос 3"],
            "model_answers": ["ответ 1", "ответ 2", "ответ 3"],
            "text": "вопрос 4",
            "final_answer": "ответ 4",
        }

        result = agent.update_user_history_context(state)

        assert result["user_history"] == ["вопрос 2", "вопрос 3", "вопрос 4"]
        assert result["model_answers"] == ["ответ 2", "ответ 3", "ответ 4"]

    def test_maintains_one_to_one_sync_after_trim(self, agent):
        state = {
            "user_history": ["вопрос 1", "вопрос 2"],
            "model_answers": ["ответ 1", "ответ 2"],
            "text": "вопрос 3",
            "final_answer": "ответ 3",
        }

        result = agent.update_user_history_context(state)

        assert len(result["user_history"]) == len(result["model_answers"])
        assert result["user_history"][-1] == "вопрос 3"
        assert result["model_answers"][-1] == "ответ 3"
