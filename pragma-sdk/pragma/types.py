from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FirewallAction(str, Enum):
    BLOCK = "block"
    OVERRIDE_REQUIRED = "override_required"
    ALLOW = "allow"


@dataclass
class RegulatoryRef:
    law: str
    jurisdiction: str
    description: str
    url: str
    triggered_by: str


@dataclass
class ComplianceResult:
    firewall_action: FirewallAction
    should_block: bool
    confidence_score: float
    risk_flags: list[str]
    recommendation: str
    violations: list[RegulatoryRef] = field(default_factory=list)
    kantian_analysis: str = ""
    utilitarian_analysis: str = ""
    virtue_ethics_analysis: str = ""
    provider: str = ""
    audit_log_id: int | None = None
    proxy_variables_detected: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ComplianceResult":
        violations = [
            RegulatoryRef(
                law=r.get("law", ""),
                jurisdiction=r.get("jurisdiction", ""),
                description=r.get("description", ""),
                url=r.get("url", ""),
                triggered_by=r.get("triggered_by", ""),
            )
            for r in data.get("regulatory_refs", [])
        ]
        return cls(
            firewall_action=FirewallAction(data.get("firewall_action", "allow")),
            should_block=data.get("should_block", False),
            confidence_score=data.get("confidence_score", 0.0),
            risk_flags=data.get("risk_flags", []),
            recommendation=data.get("recommendation", ""),
            violations=violations,
            kantian_analysis=data.get("kantian_analysis", ""),
            utilitarian_analysis=data.get("utilitarian_analysis", ""),
            virtue_ethics_analysis=data.get("virtue_ethics_analysis", ""),
            provider=data.get("provider", ""),
            audit_log_id=data.get("audit_log_id"),
            proxy_variables_detected=data.get("proxy_variables_detected", []),
        )


@dataclass
class PragmaConfig:
    pragma_api_key: str
    base_url: str = "https://api.pragma.ai"
    policy_id: str = "default"
    mode: str = "block"  # "block" | "flag" | "audit"
    block_threshold: float = 0.8
    category: str = "other"
    timeout: float = 30.0

    def __post_init__(self) -> None:
        if self.mode not in ("block", "flag", "audit"):
            raise ValueError(f"mode must be 'block', 'flag', or 'audit', got {self.mode!r}")
        if not 0.0 <= self.block_threshold <= 1.0:
            raise ValueError("block_threshold must be between 0.0 and 1.0")
        self.base_url = self.base_url.rstrip("/")


@dataclass
class EvaluationRequest:
    decision: str
    context: dict[str, Any] = field(default_factory=dict)
    category: str = "other"
    block_threshold: float = 0.8
