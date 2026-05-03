import pytest
import httpx
import respx
from pragma.evaluator import PragmaEvaluator, AsyncPragmaEvaluator
from pragma.types import PragmaConfig, EvaluationRequest, FirewallAction
from pragma.exceptions import PragmaAPIError, ConfigurationError
from .conftest import ALLOW_RESPONSE, BLOCK_RESPONSE


BASE = "http://test.pragma.ai"


def make_config(**kwargs) -> PragmaConfig:
    defaults = dict(pragma_api_key="pragma_test", base_url=BASE)
    return PragmaConfig(**{**defaults, **kwargs})


class TestPragmaEvaluator:
    @respx.mock
    def test_evaluate_allow(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=ALLOW_RESPONSE)
        )
        ev = PragmaEvaluator(make_config())
        result = ev.evaluate(EvaluationRequest(decision="Hire the candidate"))
        assert result.firewall_action == FirewallAction.ALLOW
        assert result.should_block is False

    @respx.mock
    def test_evaluate_block(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=BLOCK_RESPONSE)
        )
        ev = PragmaEvaluator(make_config())
        result = ev.evaluate(EvaluationRequest(decision="Reject her — she is 58."))
        assert result.firewall_action == FirewallAction.BLOCK
        assert result.should_block is True
        assert "bias" in result.risk_flags
        assert len(result.violations) == 1

    @respx.mock
    def test_evaluate_401_raises_config_error(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(401, json={"detail": "Unauthorized"})
        )
        ev = PragmaEvaluator(make_config())
        with pytest.raises(ConfigurationError):
            ev.evaluate(EvaluationRequest(decision="test"))

    @respx.mock
    def test_evaluate_500_raises_api_error(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        ev = PragmaEvaluator(make_config())
        with pytest.raises(PragmaAPIError) as exc_info:
            ev.evaluate(EvaluationRequest(decision="test"))
        assert exc_info.value.status_code == 500

    @respx.mock
    def test_sends_auth_header(self):
        route = respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=ALLOW_RESPONSE)
        )
        ev = PragmaEvaluator(make_config(pragma_api_key="pragma_abc123"))
        ev.evaluate(EvaluationRequest(decision="test"))
        assert route.calls[0].request.headers["authorization"] == "Bearer pragma_abc123"

    @respx.mock
    def test_sends_decision_payload(self):
        route = respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=ALLOW_RESPONSE)
        )
        ev = PragmaEvaluator(make_config())
        ev.evaluate(EvaluationRequest(
            decision="Test decision",
            context={"gender": "female"},
            category="hiring",
            block_threshold=0.7,
        ))
        import json
        body = json.loads(route.calls[0].request.content)
        assert body["decision"] == "Test decision"
        assert body["context"]["gender"] == "female"
        assert body["category"] == "hiring"
        assert body["block_threshold"] == 0.7

    def test_context_manager(self):
        with PragmaEvaluator(make_config()) as ev:
            assert ev is not None

    @respx.mock
    def test_connection_error_raises_api_error(self):
        respx.post(f"{BASE}/evaluate-decision").mock(side_effect=httpx.ConnectError("refused"))
        ev = PragmaEvaluator(make_config())
        with pytest.raises(PragmaAPIError, match="Connection error"):
            ev.evaluate(EvaluationRequest(decision="test"))


class TestAsyncPragmaEvaluator:
    @respx.mock
    @pytest.mark.asyncio
    async def test_evaluate_allow_async(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=ALLOW_RESPONSE)
        )
        ev = AsyncPragmaEvaluator(make_config())
        result = await ev.evaluate(EvaluationRequest(decision="OK decision"))
        assert result.firewall_action == FirewallAction.ALLOW
        await ev.aclose()

    @respx.mock
    @pytest.mark.asyncio
    async def test_evaluate_block_async(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=BLOCK_RESPONSE)
        )
        async with AsyncPragmaEvaluator(make_config()) as ev:
            result = await ev.evaluate(EvaluationRequest(decision="Reject — she is 58."))
        assert result.should_block is True

    @respx.mock
    @pytest.mark.asyncio
    async def test_401_raises_config_error_async(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(401, json={"detail": "Unauthorized"})
        )
        async with AsyncPragmaEvaluator(make_config()) as ev:
            with pytest.raises(ConfigurationError):
                await ev.evaluate(EvaluationRequest(decision="test"))
