# Pragma — Business Overview

## What Pragma Is

Pragma is an AI compliance firewall: a real-time enforcement layer that screens AI decisions against regulatory policy (EU AI Act, ECOA, EEOC, CFPB, FCRA) and generates audit-ready evidence. It is the only tool that combines runtime decision blocking with a structured EU AI Act compliance certification workflow.

**Two products in one:**
1. **Firewall** — intercepts AI decisions before they execute, blocks violations, logs evidence
2. **Compliance** — 15-article EU AI Act assessment with evidence collection, score tracking, and PDF certificates

---

## The Problem

Companies deploying AI systems face two compounding pressures:

**Regulatory pressure** — The EU AI Act full enforcement deadline is **1 August 2026**. High-risk AI systems (credit scoring, hiring, healthcare, law enforcement) must be fully compliant. Fines: up to €35M or 7% of global annual turnover. NYC Local Law 144 ($1,500/day), ECOA (per-violation), and GDPR Article 22 are already actively enforced.

**Operational pressure** — Without a firewall, AI systems make discriminatory, privacy-violating, or harmful decisions in production. Once the decision executes, the damage is done — regulatory penalties, lawsuits, reputational harm.

**Why existing tools fail:**
- Enterprise GRC platforms (OneTrust, Archer) treat AI as one checkbox in a 200-item framework. No real-time enforcement.
- Pure AI governance tools (Credo AI, Holistic AI) do compliance assessment well but don't screen individual decisions at runtime.
- GenAI security tools (Prompt Security, Dynamo AI) focus on prompt injection and hallucination — they don't handle regulatory compliance.

**No tool does both.** Pragma does.

---

## Target Customer (ICP)

**Primary:** Mid-market companies (50–500 employees) deploying AI in regulated verticals who need EU AI Act compliance but don't have a dedicated AI ethics team.

**Verticals with highest urgency:**
- **Financial services** — Credit scoring, loan approvals, fraud detection (Annex III A.5 + ECOA + FCRA)
- **HR / Recruitment** — Automated hiring and screening tools (Annex III A.4 + EEOC + NYC LL 144)
- **Healthcare** — Clinical decision support, patient risk stratification (Annex III A.5)
- **Insurance** — Risk assessment and underwriting AI
- **Legal tech** — AI-assisted legal decisions (Annex III A.8)

**Champion persona:** Head of Compliance, Chief Risk Officer, or General Counsel at a fintech, HR-tech, or healthtech company that recently received a legal or regulatory inquiry about their AI systems.

**Secondary:** Enterprise legal/compliance teams who need to demonstrate compliance to regulators, auditors, or large enterprise customers in RFPs.

---

## Competitive Landscape

### Tier 1 — Direct Competitors

| Company | Overlap | Key difference |
|---|---|---|
| **FairNow** | EU AI Act risk management, SMB-accessible | Compliance-only, no runtime firewall |
| **KomplyAI** | AI compliance tooling | Appears checkbox-heavy, less evidence depth |
| **Saidot** | Regulatory mapping, risk scoring, audit logs | Enterprise-leaning, no decision firewall |
| **Holistic AI** | End-to-end governance including EU AI Act | Much larger scope, enterprise price point |
| **Credo AI** | Model inventory + risk governance workflows | Model-centric (not decision-centric), enterprise |

### Tier 2 — Partial Competitors

| Company | Overlap | Why not fully direct |
|---|---|---|
| **Modulos / Monitaur** | Audit logs, model registry, regulatory mapping | MLOps workflow focus, not compliance officer tool |
| **RevAIsor** | Ethical AI compliance for finance | Finance vertical only, no runtime firewall |
| **Inspeq AI** | Development + compliance tooling | Developer tool, not end-to-end compliance |
| **OneTrust AI Governance** | Regulatory mapping, EU AI Act module | Broad GRC platform — AI is one of 50 frameworks |
| **Deeploy** | Responsible AI model lifecycle | MLOps-first, compliance is secondary |

### Tier 3 — Adjacent (Not Direct)

| Company | Why not a competitor |
|---|---|
| **Microsoft Purview / IBM watsonx** | Enterprise giants — AI compliance is one module inside massive platforms |
| **Prompt Security / Dynamo AI** | GenAI security (prompt injection, hallucination, data leakage) — different problem |
| **Vanta** | Cloud compliance (SOC2, ISO 27001) — not AI-specific |
| **Archer / Mitratech** | Traditional GRC platforms bolting on AI — heavy implementation |

---

## Where Pragma Wins

### 1. Firewall + Compliance in one product
Every competitor does one or the other. Pragma is the only tool where the same platform that screens AI decisions in real-time also produces the EU AI Act compliance certificate. This is a structural moat — companies that need both don't have to buy and integrate two separate tools.

**The pitch:** *"Credo AI and FairNow tell you whether your AI system is compliant on paper. Pragma also stops it from making a discriminatory or high-risk decision in production."*

### 2. Deep fintech compliance — not just EU AI Act
Pragma's lending firewall covers the full regulatory stack for credit decisions:
- HOLC redlining geo detection (500+ zip codes, 35 US cities)
- ECOA §1002.9 adverse action written notice requirement
- FCRA §615(a) consumer reporting disclosure
- EEOC 4/5ths disparate impact analysis
- State law overlays (CA FEHA, NY HRL, IL HRA)
- 14 indirect phrasing patterns ("that part of town", "near retirement", "family obligations")

No other tool generates a production-ready adverse action notice in one API call.

### 3. Evidence depth — not self-declaration
Most competitors accept a checkbox as compliance evidence. Pragma introduced two AI-powered evidence mechanisms:
- **Document upload** — upload your FRIA PDF, QMS certificate, training records → Claude reads and validates against the specific article requirement
- **Guided interview** — answer 5 structured questions per article → Claude scores the quality of compliance evidence and identifies gaps

Pragma compliance verdicts are defensible to regulators in a way that self-declaration tools are not.

### 4. Dynamic rule engine — enterprise-grade configurability
Compliance rules live in the database, not code. Enterprise orgs can:
- Change a FAIL to FLAG for a specific rule without filing a change request
- Adjust proxy detection thresholds for their risk tolerance
- Enable/disable jurisdiction-specific overlays
- Add custom rule configs that apply to their org only

All changes are auditable and take effect immediately with no deployment.

### 5. Speed to value
5-minute wizard. No implementation project, no professional services, no 6-month enterprise sales cycle. A compliance officer can register their first AI system and get a certificate in under an hour.

### 6. Audit trail tied to decisions
The `audit_log` links every AI decision to the compliance record. W3C PROV JSON-LD export gives regulators and GRC tools the format they expect — not a CSV, not a PDF, but a machine-readable provenance document.

---

## Pricing

| Plan | Price | Evaluations/month | Target |
|---|---|---|---|
| Free | $0 | 100 | Exploration, demo |
| Growth | $299/mo | 2,000 | Active deployment |
| Enterprise | Contact sales | Unlimited | Large accounts, custom SLAs |

**Pricing rationale:** The $299 Growth plan is positioned below the cheapest enterprise AI governance tools (typically $500+/seat/month). The evaluation-based meter aligns cost with usage — a company with 1,000 AI decisions/month is clearly in production, not just evaluating.

---

## Key Metrics to Track

| Metric | Why it matters |
|---|---|
| DAU / WAU / MAU | Active user cadence — available in admin analytics dashboard |
| Systems registered per user | Proxy for production deployment, not just exploration |
| Compliance score over time | Dashboard trend — improving score = engaged customer |
| Evidence upload / interview completion rate | Depth of engagement with compliance workflow |
| Certificate downloads | Strongest signal of intent for regulatory submission |
| `decision_evaluated` event volume | Firewall in production usage |
| `report_downloaded` / `audit_exported` events | Evidence generation usage |
| Plan distribution (free → growth conversion) | Monetization health |
| Feature adoption (from admin analytics panel) | Identifies which features drive retention |
| Email notification open rate (gap reminders) | Leading indicator of re-engagement |

---

## Regulatory Tailwinds

The EU AI Act enforcement timeline creates an urgent, time-bound compliance market:

| Date | Milestone |
|---|---|
| Feb 2025 | Art. 4 (AI Literacy) in force |
| Aug 2025 | Art. 5 (Prohibited practices) in force |
| **Aug 2026** | **Full high-risk AI obligations — Arts. 9–15, 17, 25, 27, 30, 33** |
| 2027 | Art. 6 general-purpose AI model obligations |

NYC Local Law 144 is already enforced ($1,500/day per violation). GDPR Article 22 and ECOA are actively enforced. CFPB issued updated algorithmic discrimination guidance in 2024.

---

## Roadmap

### Completed
- ✅ AI decision firewall (real-time screening, L1 deterministic + L2 LLM)
- ✅ EU AI Act 15-article compliance engine
- ✅ PDF compliance certificate generation
- ✅ LoanSight AI demo system (Veridian Finance SA)
- ✅ Email notifications (welcome, gap reminders, deadline countdown)
- ✅ Compliance dashboard (score trends, article heatmap)
- ✅ AI-powered evidence collection (document upload + guided interview)
- ✅ HOLC geo redlining detection (500+ zip codes, 35 US cities)
- ✅ ECOA §1002.9 adverse action notice generator
- ✅ Disparate impact analysis (EEOC 4/5ths rule)
- ✅ Dynamic rule engine (DB-backed, per-org overrides)
- ✅ Indirect phrasing pattern detection (14 categories)
- ✅ State law overlays (CA, NY, IL)
- ✅ W3C PROV JSON-LD audit export
- ✅ API key management + API traffic dashboard
- ✅ Customer analytics (PostHog + own DB — DAU/WAU/MAU, feature adoption)
- ✅ Admin analytics dashboard (in-app, admin-only)
- ✅ Lending vertical landing page (lending.usepragma.co)

### Deferred
- ⏳ Evidence staleness tracking (flag evidence older than 12 months)
- ⏳ Remediation action plans (step-by-step gap resolution per article)
- ⏳ Conformity assessment workflow (full Annex VI self-assessment form)
- ⏳ EU AI Act regulatory update feed (auto-update as guidance evolves)
- ⏳ NIST AI RMF framework support
- ⏳ Webhook delivery (push compliance alerts to customer systems)
- ⏳ HIPAA / healthcare vertical overlays
- ⏳ Multi-language support (EU market)
