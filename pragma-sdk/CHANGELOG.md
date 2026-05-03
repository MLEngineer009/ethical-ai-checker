# Changelog

All notable changes to `pragma-sdk` will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-04-29

### Added

- `Pragma()` factory — wraps any `openai.OpenAI` or `openai.AzureOpenAI` client with one line. Every `client.chat.completions.create()` call is evaluated by the Pragma firewall before the underlying model is called.
- `AsyncPragma()` factory — same as `Pragma()` but wraps `AsyncOpenAI` / `AsyncAzureOpenAI` for async codebases.
- Three enforcement modes:
  - `"block"` (default) — raises `ComplianceError` when `should_block=True`.
  - `"flag"` — attaches `.pragma_result` to the response; never raises.
  - `"audit"` — evaluates silently, forwards all calls; useful for logging without blocking.
- `ComplianceError` — carries a full `ComplianceResult` (firewall action, risk flags, regulatory refs, confidence score).
- `ComplianceResult.from_dict()` — deserializes the Pragma API response into a typed object.
- `FirewallAction` enum — `block`, `override_required`, `allow`.
- `RegulatoryRef` dataclass — structured reference to a specific regulation (EEOC, EU AI Act, GDPR, NYC LL144, CFPB).
- `pragma_context` and `pragma_category` keyword args — passed to `completions.create()`, forwarded to the Pragma backend, stripped before the OpenAI call.
- Proxy variable detection — `ComplianceResult.proxy_variables_detected` surfaces ECOA/Regulation B proxy fields (zip_code, last_name, ip_country, etc.) in the `ComplianceError`.
- `PragmaAPIError` — raised on non-200 HTTP responses from the backend.
- `ConfigurationError` — raised on 401 (bad API key) or invalid configuration values.
- `PragmaConfig` — validated configuration dataclass. Raises `ValueError` on invalid `mode` or `block_threshold`.
- Sync (`PragmaEvaluator`) and async (`AsyncPragmaEvaluator`) HTTP clients using `httpx`.
- Full test suite (no live backend required — uses `respx` for HTTP mocking).
