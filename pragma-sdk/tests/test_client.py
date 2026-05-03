import pytest
import httpx
import respx
from unittest.mock import MagicMock, AsyncMock
from pragma import Pragma, AsyncPragma, ComplianceError
from pragma.types import FirewallAction
from pragma.exceptions import ConfigurationError
from .conftest import ALLOW_RESPONSE, BLOCK_RESPONSE, OVERRIDE_RESPONSE, PROXY_RESPONSE


BASE = "http://test.pragma.ai"


def make_openai_client(response_text: str = "Sure, here is your answer.") -> MagicMock:
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=response_text))]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


def make_async_openai_client(response_text: str = "Async answer.") -> MagicMock:
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=response_text))]
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    return mock_client


class TestPragmaFactory:
    def test_returns_wrapped_client(self):
        oai = make_openai_client()
        client = Pragma(oai, pragma_api_key="pragma_test", base_url=BASE)
        assert hasattr(client, "chat")
        assert hasattr(client.chat, "completions")

    def test_invalid_mode_raises(self):
        oai = make_openai_client()
        with pytest.raises(ValueError, match="mode must be"):
            Pragma(oai, pragma_api_key="pragma_test", base_url=BASE, mode="bad")

    def test_passthrough_attributes(self):
        oai = make_openai_client()
        oai.models = MagicMock()
        client = Pragma(oai, pragma_api_key="pragma_test", base_url=BASE)
        assert client.models is oai.models


class TestBlockMode:
    @respx.mock
    def test_allow_passes_through_to_openai(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=ALLOW_RESPONSE)
        )
        oai = make_openai_client("Here is the answer.")
        client = Pragma(oai, pragma_api_key="pragma_test", base_url=BASE, mode="block")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "What is 2+2?"}],
        )
        assert response is not None
        oai.chat.completions.create.assert_called_once()

    @respx.mock
    def test_block_raises_compliance_error(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=BLOCK_RESPONSE)
        )
        oai = make_openai_client()
        client = Pragma(oai, pragma_api_key="pragma_test", base_url=BASE, mode="block")
        with pytest.raises(ComplianceError) as exc_info:
            client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Reject her — she is 58."}],
            )
        err = exc_info.value
        assert err.result.firewall_action == FirewallAction.BLOCK
        assert "bias" in err.result.risk_flags
        assert len(err.result.violations) == 1
        oai.chat.completions.create.assert_not_called()

    @respx.mock
    def test_override_required_does_not_block_by_default(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=OVERRIDE_RESPONSE)
        )
        oai = make_openai_client()
        client = Pragma(oai, pragma_api_key="pragma_test", base_url=BASE, mode="block")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Borderline decision."}],
        )
        assert response is not None
        oai.chat.completions.create.assert_called_once()

    @respx.mock
    def test_block_openai_never_called(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=BLOCK_RESPONSE)
        )
        oai = make_openai_client()
        client = Pragma(oai, pragma_api_key="pragma_test", base_url=BASE)
        try:
            client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Reject her."}],
            )
        except ComplianceError:
            pass
        oai.chat.completions.create.assert_not_called()


class TestFlagMode:
    @respx.mock
    def test_flag_mode_attaches_result_on_allow(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=ALLOW_RESPONSE)
        )
        oai = make_openai_client()
        client = Pragma(oai, pragma_api_key="pragma_test", base_url=BASE, mode="flag")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Safe message."}],
        )
        assert hasattr(response, "pragma_result")
        assert response.pragma_result.firewall_action == FirewallAction.ALLOW

    @respx.mock
    def test_flag_mode_does_not_raise_on_block(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=BLOCK_RESPONSE)
        )
        oai = make_openai_client()
        client = Pragma(oai, pragma_api_key="pragma_test", base_url=BASE, mode="flag")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Reject her — she is 58."}],
        )
        # should_block=True but mode=flag, so no exception raised
        assert hasattr(response, "pragma_result")
        assert response.pragma_result.should_block is True


class TestAuditMode:
    @respx.mock
    def test_audit_mode_passes_through_silently(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=BLOCK_RESPONSE)
        )
        oai = make_openai_client()
        client = Pragma(oai, pragma_api_key="pragma_test", base_url=BASE, mode="audit")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Reject her — she is 58."}],
        )
        assert response is not None
        oai.chat.completions.create.assert_called_once()


class TestProxyVariables:
    @respx.mock
    def test_proxy_vars_in_compliance_error(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=PROXY_RESPONSE)
        )
        oai = make_openai_client()
        client = Pragma(oai, pragma_api_key="pragma_test", base_url=BASE)
        with pytest.raises(ComplianceError) as exc_info:
            client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Deny loan based on zip."}],
                pragma_context={"zip_code": "90210"},
                pragma_category="finance",
            )
        result = exc_info.value.result
        assert len(result.proxy_variables_detected) == 1
        assert result.proxy_variables_detected[0]["field"] == "zip_code"


class TestCustomContext:
    @respx.mock
    def test_pragma_context_forwarded(self):
        route = respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=ALLOW_RESPONSE)
        )
        oai = make_openai_client()
        client = Pragma(oai, pragma_api_key="pragma_test", base_url=BASE, mode="flag")
        client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Evaluate candidate."}],
            pragma_context={"experience": 5, "role": "engineer"},
            pragma_category="hiring",
        )
        import json
        body = json.loads(route.calls[0].request.content)
        assert body["context"]["experience"] == 5
        assert body["category"] == "hiring"

    @respx.mock
    def test_pragma_kwargs_stripped_before_openai(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=ALLOW_RESPONSE)
        )
        oai = make_openai_client()
        client = Pragma(oai, pragma_api_key="pragma_test", base_url=BASE)
        client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Test."}],
            pragma_context={"key": "val"},
            pragma_category="hiring",
        )
        call_kwargs = oai.chat.completions.create.call_args.kwargs
        assert "pragma_context" not in call_kwargs
        assert "pragma_category" not in call_kwargs


class TestAsyncPragma:
    @respx.mock
    @pytest.mark.asyncio
    async def test_async_allow(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=ALLOW_RESPONSE)
        )
        oai = make_async_openai_client()
        client = AsyncPragma(oai, pragma_api_key="pragma_test", base_url=BASE)
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Safe message."}],
        )
        assert response is not None
        oai.chat.completions.create.assert_awaited_once()

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_block_raises(self):
        respx.post(f"{BASE}/evaluate-decision").mock(
            return_value=httpx.Response(200, json=BLOCK_RESPONSE)
        )
        oai = make_async_openai_client()
        client = AsyncPragma(oai, pragma_api_key="pragma_test", base_url=BASE, mode="block")
        with pytest.raises(ComplianceError) as exc_info:
            await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Reject her — she is 58."}],
            )
        assert exc_info.value.result.should_block is True
        oai.chat.completions.create.assert_not_awaited()
