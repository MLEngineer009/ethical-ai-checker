from __future__ import annotations
from typing import Any
from .types import PragmaConfig
from .providers.openai import PragmaOpenAI, AsyncPragmaOpenAI


def Pragma(
    openai_client: Any,
    *,
    pragma_api_key: str,
    policy_id: str = "default",
    base_url: str = "https://api.pragma.ai",
    mode: str = "block",
    block_threshold: float = 0.8,
    category: str = "other",
    timeout: float = 30.0,
) -> PragmaOpenAI:
    """
    Wrap an OpenAI (or AzureOpenAI) client with Pragma compliance enforcement.

    Every call to ``client.chat.completions.create()`` is evaluated by the
    Pragma firewall before the underlying model is called.

    Args:
        openai_client: An ``openai.OpenAI`` or ``openai.AzureOpenAI`` instance.
        pragma_api_key: Your Pragma API key (``pragma_*`` prefix).
        policy_id: Policy identifier for audit trail grouping.
        base_url: Pragma backend URL. Defaults to the hosted API.
        mode: ``"block"`` raises :exc:`ComplianceError` on violations,
              ``"flag"`` attaches ``.pragma_result`` to the response,
              ``"audit"`` logs silently.
        block_threshold: Confidence threshold (0–1) for hard blocks. Default 0.8.
        category: Default decision category (hiring/finance/healthcare/…).
        timeout: HTTP request timeout in seconds.

    Returns:
        A :class:`PragmaOpenAI` proxy that behaves like the original client.

    Example::

        from openai import OpenAI
        from pragma import Pragma, ComplianceError

        client = Pragma(
            OpenAI(),
            pragma_api_key="pragma_...",
            policy_id="hr-v1",
        )

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Reject her — she's 58."}],
            )
        except ComplianceError as e:
            print(e.result.firewall_action)  # "block"
    """
    config = PragmaConfig(
        pragma_api_key=pragma_api_key,
        base_url=base_url,
        policy_id=policy_id,
        mode=mode,
        block_threshold=block_threshold,
        category=category,
        timeout=timeout,
    )
    return PragmaOpenAI(openai_client, config)


def AsyncPragma(
    openai_client: Any,
    *,
    pragma_api_key: str,
    policy_id: str = "default",
    base_url: str = "https://api.pragma.ai",
    mode: str = "block",
    block_threshold: float = 0.8,
    category: str = "other",
    timeout: float = 30.0,
) -> AsyncPragmaOpenAI:
    """
    Async variant of :func:`Pragma`. Wraps ``AsyncOpenAI`` or ``AsyncAzureOpenAI``.

    Usage is identical to :func:`Pragma` but ``client.chat.completions.create()``
    must be awaited.
    """
    config = PragmaConfig(
        pragma_api_key=pragma_api_key,
        base_url=base_url,
        policy_id=policy_id,
        mode=mode,
        block_threshold=block_threshold,
        category=category,
        timeout=timeout,
    )
    return AsyncPragmaOpenAI(openai_client, config)
