import pytest
from pragma.types import ComplianceResult, FirewallAction, PragmaConfig, EvaluationRequest, RegulatoryRef
from pragma.exceptions import ConfigurationError


class TestFirewallAction:
    def test_values(self):
        assert FirewallAction.BLOCK == "block"
        assert FirewallAction.OVERRIDE_REQUIRED == "override_required"
        assert FirewallAction.ALLOW == "allow"

    def test_from_string(self):
        assert FirewallAction("block") is FirewallAction.BLOCK


class TestComplianceResult:
    def test_from_dict_allow(self):
        data = {
            "firewall_action": "allow",
            "should_block": False,
            "confidence_score": 0.1,
            "risk_flags": [],
            "recommendation": "OK",
            "regulatory_refs": [],
        }
        result = ComplianceResult.from_dict(data)
        assert result.firewall_action == FirewallAction.ALLOW
        assert result.should_block is False
        assert result.violations == []

    def test_from_dict_block_with_refs(self):
        data = {
            "firewall_action": "block",
            "should_block": True,
            "confidence_score": 0.92,
            "risk_flags": ["bias", "discrimination"],
            "recommendation": "Stop.",
            "regulatory_refs": [
                {
                    "law": "EEOC Title VII",
                    "jurisdiction": "US",
                    "description": "Prohibits sex discrimination.",
                    "url": "https://eeoc.gov",
                    "triggered_by": "bias",
                }
            ],
        }
        result = ComplianceResult.from_dict(data)
        assert result.firewall_action == FirewallAction.BLOCK
        assert result.should_block is True
        assert len(result.violations) == 1
        assert result.violations[0].law == "EEOC Title VII"

    def test_from_dict_defaults(self):
        result = ComplianceResult.from_dict({})
        assert result.firewall_action == FirewallAction.ALLOW
        assert result.confidence_score == 0.0
        assert result.risk_flags == []
        assert result.audit_log_id is None
        assert result.proxy_variables_detected == []

    def test_proxy_variables(self):
        data = {
            "firewall_action": "block",
            "should_block": True,
            "confidence_score": 0.9,
            "risk_flags": ["bias"],
            "recommendation": "",
            "regulatory_refs": [],
            "proxy_variables_detected": [
                {"field": "zip_code", "value": "90210", "risk": "redlining", "regulation": "ECOA"}
            ],
        }
        result = ComplianceResult.from_dict(data)
        assert len(result.proxy_variables_detected) == 1
        assert result.proxy_variables_detected[0]["field"] == "zip_code"


class TestPragmaConfig:
    def test_defaults(self):
        cfg = PragmaConfig(pragma_api_key="pragma_test")
        assert cfg.mode == "block"
        assert cfg.block_threshold == 0.8
        assert cfg.base_url == "https://api.pragma.ai"

    def test_trailing_slash_stripped(self):
        cfg = PragmaConfig(pragma_api_key="x", base_url="http://localhost:8000/")
        assert cfg.base_url == "http://localhost:8000"

    def test_invalid_mode(self):
        with pytest.raises(ValueError, match="mode must be"):
            PragmaConfig(pragma_api_key="x", mode="invalid")

    def test_invalid_threshold_too_high(self):
        with pytest.raises(ValueError, match="block_threshold"):
            PragmaConfig(pragma_api_key="x", block_threshold=1.5)

    def test_invalid_threshold_negative(self):
        with pytest.raises(ValueError, match="block_threshold"):
            PragmaConfig(pragma_api_key="x", block_threshold=-0.1)

    def test_valid_modes(self):
        for mode in ("block", "flag", "audit"):
            cfg = PragmaConfig(pragma_api_key="x", mode=mode)
            assert cfg.mode == mode


class TestEvaluationRequest:
    def test_defaults(self):
        req = EvaluationRequest(decision="test")
        assert req.context == {}
        assert req.category == "other"
        assert req.block_threshold == 0.8
