from ..states import AgentState
from langchain_core.prompts import ChatPromptTemplate

class BaseAgentNodes:
    HISTORY_LIMIT = 10 # TO DO: поправить настройку с лимитом истории запросов.

    async def validate_text(self, state: AgentState) -> AgentState:
        """ Проверяем, что текст вопроса пользователя соответсвует публичной политики.

            Notes:
                1. Нода для детектирования спам запросов на агента;
                2. Кешируем глобально вопросы к агенту в общий топик Redis;

            Return:
                Бинарное значение - спам или нормальный вопрос к агенту.
        """
        question = state["text"]
        try:
            cached_result = self.cache.get \
                    (
                    meta_info="validate_input",
                    query=question
                )
            if cached_result:
                state["is_valid"] = cached_result.get("json").get("is_valid")
                state["final_answer"] = cached_result.get("json").get("final_answer")
                return state
            else:
                prompt = ChatPromptTemplate.from_template \
                        (
                        self.langfuse_client.get_prompt("policy_validation").get_langchain_prompt()
                    )
                chain = prompt | self.llm
                output = await chain.ainvoke \
                        (
                        {
                            "text": state["text"]
                        }
                    )
                output = output.content.strip().lower()

            is_valid = "да" in output

            cache_data = {"is_valid": is_valid}

            if not is_valid:
                cache_data["final_answer"] = "Не прошёл валидацию"
                state["final_answer"] = cache_data["final_answer"]

            state["is_valid"] = is_valid
            self.cache.save(
                meta_info="validate_input",
                query=question,
                output="",
                json_data=cache_data)
            return state

        except Exception as e:
            print(f"Validate error at validate_input: {e}")

    async def validate_final_answer(self, state: AgentState) -> AgentState:
        """ Проверяем, что текст ответа модели соответсвует публичной политики.

            Notes:
                1. Нода для детектирования спам запросов на агента;
                2. Кешируем глобально вопросы к агенту в общий топик Redis;

            Return:
                Бинарное значение - спам или нормальный ответ от агента.
        """
        final_answer = state.get("final_answer", "")
        try:
            cached_result = self.cache.get \
                    (
                    meta_info="validate_final_answer",
                    query=final_answer
                )
            if cached_result:
                state["is_valid"] = cached_result.get("json").get("is_valid") or True
                return state
            else:
                prompt = self.langfuse_client.get_prompt("policy_validation").get_langchain_prompt()
                prompt = ChatPromptTemplate.from_template(prompt)
                chain = prompt | self.llm
                output = await chain.ainvoke \
                        (
                        {
                            "text": final_answer
                        }
                    )

                is_valid = "да" in output.content.strip().lower()
                cache_data = {"answer": is_valid}
                if not is_valid:
                    state["final_answer"] = "Не прошёл валидацию"
                state["is_valid"] = is_valid
                self.cache.save \
                        (
                        meta_info="validate_final_answer",
                        query=final_answer,
                        output="",
                        json_data=cache_data
                    )
                return state

        except Exception as e:
            print(f"Error at validate_final_answer: {e}")

    def update_user_history_context(self, state: AgentState) -> AgentState:
        """Обновляет историю вопросов/ответов: аппендит текущий вопрос + ответ, тримирует до HISTORY_LIMIT.

        Args:
            state: Текущее состояние с user_history, model_answers, text (текущий вопрос), final_answer (ответ).

        Returns:
            Обновленное состояние с синхронизированной историей (последние HISTORY_LIMIT пар вопрос-ответ).
        """
        if state.get("user_history"):
            state["user_history"].append(state["text"])
        else:
            state["user_history"] = [state["text"]]

        if state.get("model_answers"):
            state["model_answers"].append(state.get("final_answer", ""))
        else:
            state["model_answers"] = [state["final_answer"]]

        if len(state["user_history"]) > self.HISTORY_LIMIT:
            trim_count = len(state["user_history"]) - self.HISTORY_LIMIT
            state["user_history"] = state["user_history"][-self.HISTORY_LIMIT:]
            state["model_answers"] = state["model_answers"][-trim_count:]

        return {
            "user_history": state["user_history"],
            "model_answers": state["model_answers"]
        }

    def reject_stub(self, state: AgentState) -> AgentState:
        """ Логика ответа в случае какой-либо поломки в агенте при генерации ответа.
        """
        state["final_answer"] = ("Возможно текст не соответствует тематике вопросов для диалога с чат-ботом. "
                                 "Пожалуйста, повторите свой вопрос еще раз.")
        return state