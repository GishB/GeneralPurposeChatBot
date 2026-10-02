from service.config import ChromaSettings, LLMSettings, PostgreSettings


class TestChromaDefaults:
    def test_topk_documents_default(self):
        settings = ChromaSettings()

        assert settings.chroma_topk_documents == 5


class TestPostgresDefaults:
    def test_answer_max_concurrent_default(self):
        settings = PostgreSettings()

        assert settings.answer_max_concurrent == 8


class TestSummaryParams:
    def test_uses_dedicated_summary_model(self):
        settings = LLMSettings()

        assert settings.summary_params["model"] == "deepseek/deepseek-v4-pro"

    def test_extra_body_has_no_provider_order(self):
        settings = LLMSettings()

        extra_body = settings.summary_params.get("extra_body")
        # extra_body может быть None или содержать только reasoning — но НИКОГДА provider.
        if extra_body is not None:
            assert "provider" not in extra_body

    def test_provider_order_env_is_ignored_for_summary(self):
        settings = LLMSettings(
            openrouter_provider_order="wandb/fp8,digitalocean,baidu/fp8",
            openrouter_allow_fallbacks=False,
        )

        extra_body = settings.summary_params.get("extra_body")
        if extra_body is not None:
            assert "provider" not in extra_body


class TestFallbackParams:
    def test_default_fallback_uses_simple_model(self):
        settings = LLMSettings()

        assert settings.fallback_params["model"] == settings.fallback_llm_model_name

    def test_complex_fallback_uses_complex_model(self):
        settings = LLMSettings()

        assert settings.fallback_params_complex["model"] == settings.fallback_llm_model_name_complex

    def test_decompose_fallback_uses_decompose_model(self):
        settings = LLMSettings()

        assert settings.fallback_params_decompose["model"] == settings.fallback_llm_model_name_decompose

    def test_fallback_api_key_preferred_over_openai_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        settings = LLMSettings(fallback_llm_api_key="explicit-key")

        assert settings.fallback_params["openai_api_key"] == "explicit-key"

    def test_fallback_api_key_falls_back_to_openai_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        settings = LLMSettings(fallback_llm_api_key="")

        assert settings.fallback_params["openai_api_key"] == "env-key"

    def test_fallback_disabled_without_api_base(self):
        settings = LLMSettings(fallback_llm_api_base="")

        assert settings.fallback_params is None
        assert settings.fallback_params_complex is None


class TestReasoningNodeParams:
    def test_defaults_to_base_model(self):
        settings = LLMSettings()

        assert settings.reasoning_node_params["model"] == settings.model_name

    def test_uses_dedicated_decompose_model(self):
        settings = LLMSettings(decompose_model_name="gpt://folder-id/qwen3-235b-a22b-fp8")

        assert settings.reasoning_node_params["model"] == "gpt://folder-id/qwen3-235b-a22b-fp8"


class TestRequestTimeout:
    def test_default_timeout_applied_to_all_roles(self):
        settings = LLMSettings()

        assert settings.base_params["request_timeout"] == 60
        assert settings.reasoning_node_params["request_timeout"] == 60
        assert settings.validation_params["request_timeout"] == 60
        assert settings.summary_params["request_timeout"] == 60
        assert settings.critic_params["request_timeout"] == 60
        assert settings.fallback_params["request_timeout"] == 60

    def test_timeout_from_env(self):
        settings = LLMSettings(request_timeout_seconds=45)

        assert settings.base_params["request_timeout"] == 45
        assert settings.fallback_params_complex["request_timeout"] == 45
        assert settings.fallback_params_decompose["request_timeout"] == 45


class TestCriticParams:
    def test_uses_dedicated_critic_model(self):
        settings = LLMSettings()

        assert settings.critic_params["model"] == "deepseek/deepseek-v4-pro"

    def test_extra_body_has_no_provider_order(self):
        settings = LLMSettings()

        extra_body = settings.critic_params.get("extra_body")
        # extra_body может быть None или содержать только reasoning — но НИКОГДА provider.
        if extra_body is not None:
            assert "provider" not in extra_body

    def test_provider_order_env_is_ignored_for_critic(self):
        settings = LLMSettings(
            openrouter_provider_order="wandb/fp8,digitalocean,baidu/fp8",
            openrouter_allow_fallbacks=False,
        )

        extra_body = settings.critic_params.get("extra_body")
        if extra_body is not None:
            assert "provider" not in extra_body
