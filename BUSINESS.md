# Pragma — Business Overview

## What Pragma Is

Pragma is an AI compliance firewall: a real-time enforcement layer that screens AI decisions against regulatory policy (EU AI Act, EEOC, GDPR, CFPB) and generates audit-ready evidence. It is the only tool that combines runtime decision blocking with a structured EU AI Act compliance certification workflow.

**Two products in one:**
1. **Firewall** — intercepts AI decisions before they execute, blocks violations, logs evidence
2. **Compliance** — 15-article EU AI Act assessment with evidence collection, score tracking, and PDF certificates

---

## The Problem

Companies deploying AI systems face two compounding pressures:

**Regulatory pressure** — The EU AI Act full enforcement deadline is **1 August 2026**. High-risk AI systems (credit scoring, hiring, healthcare, law enforcement) must be fully compliant by then. Fines: up to €35M or 7% of global annual turnover. Similar timelines exist for NYC Local Law 144 ($1,500/day) and GDPR Article 22.

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
- **Financial services** — Credit scoring, loan approvals, fraud detection (Annex III A.5)
- **HR / Recruitment** — Automated hiring and screening tools (Annex III A.4)
- **Healthcare** — Clinical decision support, patient risk stratification (Annex III A.5)
- **Insurance** — Risk assessment and underwriting AI
- **Legal tech** — AI-assisted legal decisions (Annex III A.8)

**Champion persona:** Head of Compliance, Chief Risk Officer, or General Counsel at a fintech, HR-tech, or healthtech company that recently received a legal or regulatory inquiry about their AI systems.

**Secondary:** Enterprise legal/compliance teams who need to demonstrate compliance to regulators, auditors, or large enterprise customers in RFPs.

---

## Competitive Landscape

### Tier 1 — Direct Competitors

Companies doing similar work for a similar buyer:

| Company | Overlap | Key difference |
|---|---|---|
| **FairNow** | EU AI Act risk management, SMB-accessible | Compliance-only, no runtime firewall |
| **KomplyAI** | AI compliance tooling | Appears checkbox-heavy, less evidence depth |
| **Saidot** | Regulatory mapping, risk scoring, audit logs | Enterprise-leaning, no decision firewall |
| **Holistic AI** | End-to-end governance including EU AI Act | Much larger scope, enterprise price point |
| **Credo AI** | Model inventory + risk governance workflows | Model-centric (not decision-centric), enterprise |

### Tier 2 — Partial Competitors

Overlapping on features but different angle or market segment:

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
| **Microsoft Purview / IBM watsonx** | Enterprise giants — AI compliance is one module inside massive platforms; completely different sales motion and buyer |
| **Prompt Security / Dynamo AI** | GenAI security (prompt injection, hallucination, data leakage) — different problem, different buyer |
| **Vanta** | Cloud compliance (SOC2, ISO 27001) — not AI-specific |
| **Archer / Mitratech / Centraleyes** | Traditional GRC platforms bolting on AI — heavy implementation, not AI-native |
| **SAS / C3 AI** | Enterprise analytics — regulated industries but not EU AI Act compliance tooling |

---

## Where Pragma Wins

### 1. Firewall + Compliance in one product
Every competitor does one or the other. Pragma is the only tool where the same platform that screens AI decisions in real-time also produces the EU AI Act compliance certificate. This is a structural moat — companies that need both don't have to buy and integrate two separate tools.

**The pitch:** *"Credo AI and FairNow tell you whether your AI system is compliant on paper. Pragma also stops it from making a discriminatory or high-risk decision in production."*

### 2. Evidence depth — not self-declaration
Most competitors accept a checkbox as compliance evidence. Pragma introduced two AI-powered evidence mechanisms:
- **Document upload** — upload your FRIA PDF, QMS certificate, training records → Claude reads and validates it against the specific article requirement
- **Guided interview** — answer 5 structured questions per article → Claude scores the quality of your compliance evidence and identifies gaps

This means Pragma compliance verdicts are defensible to regulators in a way that self-declaration tools are not.

### 3. Speed to value
5-minute wizard. No implementation project, no professional services, no 6-month enterprise sales cycle. A compliance officer can register their first AI system and get a certificate in under an hour.

### 4. Audit trail tied to decisions
The `audit_log` links every AI decision to the compliance record. When a regulator asks "show me your decision audit trail for this loan rejection," Pragma can produce it with the regulatory refs that were evaluated, the human oversight overrides recorded, and the proxy variables detected — all linked to the system's EU AI Act compliance status.

### 5. Demo-ready
The LoanSight AI demo (Veridian Finance SA credit scoring system) produces a realistic PASS/PARTIAL/FAIL compliance profile in under 2 minutes. One button click. No sales engineering needed for a first demo.

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
| Systems registered per user | Proxy for production deployment, not just exploration |
| Compliance score over time | Dashboard trend — improving score = engaged customer |
| Evidence upload / interview completion rate | Depth of engagement with the compliance workflow |
| Certificate downloads | Strongest signal of intent to use for regulatory submission |
| Email notification open rate (gap reminders) | Leading indicator of re-engagement |
| Time to first compliance check | Activation metric |

---

## Roadmap Context

Features completed:
- ✅ AI decision firewall (real-time screening)
- ✅ EU AI Act 15-article compliance engine
- ✅ PDF compliance certificate generation
- ✅ LoanSight AI demo system
- ✅ Email notifications (welcome, gap reminders, deadline countdown)
- ✅ Compliance dashboard (score trends, article heatmap)
- ✅ AI-powered evidence collection (document upload + guided interview)

Deferred:
- ⏳ Platform ops dashboard (internal Pragma team metrics)
- ⏳ Evidence staleness tracking (flag evidence older than 12 months)
- ⏳ Remediation action plans (step-by-step gap resolution)
- ⏳ Conformity assessment workflow (full Annex VI self-assessment form)
- ⏳ EU AI Act regulatory update feed (auto-update as guidance evolves)
- ⏳ NIST AI RMF framework support

---

## Regulatory Tailwinds

The EU AI Act enforcement timeline creates an urgent, time-bound compliance market:

| Date | Milestone |
|---|---|
| Feb 2025 | Art. 4 (AI Literacy) in force |
| Aug 2025 | Art. 5 (Prohibited practices) in force |
| **Aug 2026** | **Full high-risk AI obligations — Arts. 9–15, 17, 25, 27, 30, 33** |
| 2027 | Art. 6 general-purpose AI model obligations |

As of May 2026, there are **79 days** until the primary high-risk enforcement deadline. This is the core urgency driver for every sales conversation.

NYC Local Law 144 is already enforced ($1,500/day per violation). GDPR Article 22 automated decision-making provisions are actively enforced across the EU.
