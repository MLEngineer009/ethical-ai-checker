# pragma-sdk

**AI compliance firewall for Python.** Wrap any OpenAI-compatible client with one line — every LLM call is evaluated against regulatory policy (EU AI Act, EEOC, GDPR, NYC LL144, CFPB) before the model is called. Violations are blocked before they execute.

```bash
pip install pragma-sdk
```

---

## Quick Start

```python
from openai import OpenAI
from pragma import Pragma, ComplianceError

client = Pragma(
    OpenAI(),
    pragma_api_key="pragma_...",   # get at app.pragma.ai
    policy_id="hr-compliance-v1",
)

try:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Reject her — she is 58 years old."}],
    )
except ComplianceError as e:
    print(e.result.firewall_action)          # "block"
    print(e.result.risk_flags)               # ["bias", "discrimination", "fairness"]
    print(e.result.violations[0].regulation) # "EEOC Title VII (Civil Rights Act 1964)"
    print(e.result.confidence_score)         # 0.95
```

The underlying `OpenAI()` call is **never made** when a decision is blocked. The compliance check runs first.

---

## Installation

```bash
pip install pragma-sdk          # core (httpx + pydantic)
pip install "pragma-sdk[openai]" # include openai dependency
```

Requires Python 3.9+.

---

## Configuration

```python
client = Pragma(
    OpenAI(),
    pragma_api_key="pragma_...",  # required — your Pragma API key
    base_url="https://api.pragma.ai",  # or http://localhost:8000 for self-hosted
    policy_id="hr-v1",           # groups decisions in audit trail
    mode="block",                # "block" | "flag" | "audit"
    block_threshold=0.8,         # 0.0–1.0, confidence threshold for hard blocks
    category="hiring",           # default category for all evaluations
)
```

### Modes

| Mode | Behavior |
|------|----------|
| `"block"` (default) | Raises `ComplianceError` when `should_block=True`. The OpenAI call is skipped. |
| `"flag"` | Never raises. Attaches `.pragma_result` to the response object for inspection. |
| `"audit"` | Evaluates silently (logged in audit trail). All calls pass through. |

---

## Per-call Context

Pass `pragma_context` and `pragma_category` directly to `completions.create()`. They are forwarded to the Pragma backend and stripped before the OpenAI call.

```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Approve loan application."}],
    pragma_context={
        "zip_code": "90210",   # triggers ECOA proxy variable guard
        "income": 45000,
        "credit_score": 680,
    },
    pragma_category="finance",
)
```

---

## Async Support

```python
from openai import AsyncOpenAI
from pragma import AsyncPragma, ComplianceError

client = AsyncPragma(
    AsyncOpenAI(),
    pragma_api_key="pragma_...",
)

try:
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "..."}],
    )
except ComplianceError as e:
    print(e.result.firewall_action)
```

---

## Flag Mode — Inspect Without Blocking

```python
client = Pragma(OpenAI(), pragma_api_key="pragma_...", mode="flag")

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "..."}],
)

result = response.pragma_result
if result.should_block:
    print(f"Warning: {result.risk_flags} — {result.recommendation}")
else:
    print(response.choices[0].message.content)
```

---

## ComplianceResult Reference

```python
result: ComplianceResult = e.result  # from ComplianceError, or response.pragma_result

result.firewall_action       # FirewallAction.BLOCK | OVERRIDE_REQUIRED | ALLOW
result.should_block          # bool
result.confidence_score      # float 0.0–1.0
result.risk_flags            # list[str]: "bias", "discrimination", "privacy", ...
result.recommendation        # str — human-readable guidance
result.violations            # list[RegulatoryRef]
result.audit_log_id          # int | None — Pragma audit trail ID
result.proxy_variables_detected  # list[dict] — ECOA proxy fields found in context

# Per violation:
v = result.violations[0]
v.law           # "EEOC Title VII (Civil Rights Act 1964)"
v.jurisdiction  # "United States"
v.description   # "Prohibits employment discrimination based on sex."
v.url           # "https://www.eeoc.gov/..."
v.triggered_by  # "bias"
```

---

## Supported Regulations

Pragma evaluates decisions against seven regulatory frameworks:

| Regulation | Jurisdiction | Category |
|-----------|-------------|---------|
| EU AI Act (Aug 2026) | EU | All high-risk AI |
| EEOC Title VII / ADEA | US | Hiring |
| GDPR Article 22 | EU | Automated decisions |
| NYC Local Law 144 | New York City | Hiring |
| CFPB / ECOA | US | Credit & lending |
| NIST AI RMF | US | Risk management |
| FTC AI Guidance | US | Consumer protection |

---

## Self-Hosting

Point the SDK at your own Pragma backend:

```python
client = Pragma(
    OpenAI(),
    pragma_api_key="pragma_...",
    base_url="http://localhost:8000",  # your backend
)
```

See [github.com/MLEngineer009/pragma-sdk](https://github.com/MLEngineer009/pragma-sdk) for backend setup instructions.

---

## License

MIT
