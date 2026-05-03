from __future__ import annotations
import httpx
from .types import ComplianceResult, EvaluationRequest, PragmaConfig
from .exceptions import PragmaAPIError, ConfigurationError


class PragmaEvaluator:
    """Synchronous HTTP client for the Pragma compliance backend."""

    def __init__(self, config: PragmaConfig) -> None:
        self._config = config
        self._client = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            headers=self._auth_headers(),
        )

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._config.pragma_api_key}"}

    def evaluate(self, request: EvaluationRequest) -> ComplianceResult:
        payload = {
            "decision": request.decision,
            "context": request.context,
            "category": request.category,
            "block_threshold": request.block_threshold,
        }
        try:
            resp = self._client.post("/evaluate-decision", json=payload)
        except httpx.TransportError as exc:
            raise PragmaAPIError(f"Connection error: {exc}") from exc

        if resp.status_code == 401:
            raise ConfigurationError("Invalid or missing pragma_api_key")
        if not resp.is_success:
            raise PragmaAPIError(
                f"Pragma API error {resp.status_code}: {resp.text}",
                status_code=resp.status_code,
            )
        return ComplianceResult.from_dict(resp.json())

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "PragmaEvaluator":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class AsyncPragmaEvaluator:
    """Async HTTP client for the Pragma compliance backend."""

    def __init__(self, config: PragmaConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
            headers=self._auth_headers(),
        )

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._config.pragma_api_key}"}

    async def evaluate(self, request: EvaluationRequest) -> ComplianceResult:
        payload = {
            "decision": request.decision,
            "context": request.context,
            "category": request.category,
            "block_threshold": request.block_threshold,
        }
        try:
            resp = await self._client.post("/evaluate-decision", json=payload)
        except httpx.TransportError as exc:
            raise PragmaAPIError(f"Connection error: {exc}") from exc

        if resp.status_code == 401:
            raise ConfigurationError("Invalid or missing pragma_api_key")
        if not resp.is_success:
            raise PragmaAPIError(
                f"Pragma API error {resp.status_code}: {resp.text}",
                status_code=resp.status_code,
            )
        return ComplianceResult.from_dict(resp.json())

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncPragmaEvaluator":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
