from service.config import LLMSettings


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
