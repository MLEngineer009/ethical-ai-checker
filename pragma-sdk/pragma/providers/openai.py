from __future__ import annotations
from typing import Any
from ..evaluator import PragmaEvaluator, AsyncPragmaEvaluator
from ..types import ComplianceResult, EvaluationRequest, PragmaConfig, FirewallAction
from ..exceptions import ComplianceError


def _extract_decision(messages: list[dict[str, Any]]) -> str:
    """Pull the last user message as the decision text."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            return content if isinstance(content, str) else str(content)
    return ""


class _PragmaCompletions:
    def __init__(self, openai_completions: Any, evaluator: PragmaEvaluator, config: PragmaConfig) -> None:
        self._completions = openai_completions
        self._evaluator = evaluator
        self._config = config

    def create(self, **kwargs: Any) -> Any:
        messages = kwargs.get("messages", [])
        decision = _extract_decision(messages)
        context = kwargs.get("pragma_context", {})
        category = kwargs.get("pragma_category", self._config.category)

        request = EvaluationRequest(
            decision=decision,
            context=context,
            category=category,
            block_threshold=self._config.block_threshold,
        )
        result = self._evaluator.evaluate(request)

        if self._config.mode == "block" and result.should_block:
            raise ComplianceError(
                f"Request blocked by Pragma firewall: {', '.join(result.risk_flags)}",
                result=result,
            )

        # Strip pragma-specific kwargs before forwarding
        for key in ("pragma_context", "pragma_category"):
            kwargs.pop(key, None)

        response = self._completions.create(**kwargs)

        if self._config.mode == "flag":
            response.pragma_result = result

        return response


class _PragmaChat:
    def __init__(self, openai_chat: Any, evaluator: PragmaEvaluator, config: PragmaConfig) -> None:
        self.completions = _PragmaCompletions(openai_chat.completions, evaluator, config)


class PragmaOpenAI:
    """Wraps an OpenAI (or AzureOpenAI) client with Pragma firewall enforcement."""

    def __init__(self, openai_client: Any, config: PragmaConfig) -> None:
        self._client = openai_client
        self._config = config
        self._evaluator = PragmaEvaluator(config)
        self.chat = _PragmaChat(openai_client.chat, self._evaluator, config)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


class _AsyncPragmaCompletions:
    def __init__(self, openai_completions: Any, evaluator: AsyncPragmaEvaluator, config: PragmaConfig) -> None:
        self._completions = openai_completions
        self._evaluator = evaluator
        self._config = config

    async def create(self, **kwargs: Any) -> Any:
        messages = kwargs.get("messages", [])
        decision = _extract_decision(messages)
        context = kwargs.get("pragma_context", {})
        category = kwargs.get("pragma_category", self._config.category)

        request = EvaluationRequest(
            decision=decision,
            context=context,
            category=category,
            block_threshold=self._config.block_threshold,
        )
        result = await self._evaluator.evaluate(request)

        if self._config.mode == "block" and result.should_block:
            raise ComplianceError(
                f"Request blocked by Pragma firewall: {', '.join(result.risk_flags)}",
                result=result,
            )

        for key in ("pragma_context", "pragma_category"):
            kwargs.pop(key, None)

        response = await self._completions.create(**kwargs)

        if self._config.mode == "flag":
            response.pragma_result = result

        return response


class _AsyncPragmaChat:
    def __init__(self, openai_chat: Any, evaluator: AsyncPragmaEvaluator, config: PragmaConfig) -> None:
        self.completions = _AsyncPragmaCompletions(openai_chat.completions, evaluator, config)


class AsyncPragmaOpenAI:
    """Wraps an AsyncOpenAI (or AsyncAzureOpenAI) client with Pragma firewall enforcement."""

    def __init__(self, openai_client: Any, config: PragmaConfig) -> None:
        self._client = openai_client
        self._config = config
        self._evaluator = AsyncPragmaEvaluator(config)
        self.chat = _AsyncPragmaChat(openai_client.chat, self._evaluator, config)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
