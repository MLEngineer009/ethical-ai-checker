"""
Per-article guided interview questions for EU AI Act evidence collection.

Each article entry defines the questions shown to the user. Answers are
sent to evidence_analyzer.score_interview() for Claude-based scoring.
"""

from typing import Dict, List

# Articles that have wizard evidence boxes and can be deepened by interview.
# Keys match the compliance_engine article keys.
INTERVIEW_ARTICLES: Dict[str, Dict] = {
    "art_4": {
        "title": "Article 4 — AI Literacy",
        "requirement": (
            "Providers and deployers must ensure staff who operate or oversee this AI system "
            "have sufficient AI literacy — understanding of AI capabilities, limitations, "
            "and the specific risks of this system."
        ),
        "questions": [
            {"id": "q1", "text": "How many staff members operate or oversee this AI system?"},
            {"id": "q2", "text": "What AI literacy training was provided? (course name, provider, duration)"},
            {"id": "q3", "text": "When was training completed? (date, quarter, or year)"},
            {"id": "q4", "text": "How do you verify that staff understand the system's capabilities and limitations?"},
            {"id": "q5", "text": "Is training refreshed when the system is updated or risks change?"},
        ],
    },
    "art_9": {
        "title": "Article 9 — Risk Management System",
        "requirement": (
            "A continuous, iterative risk management process must be established and documented "
            "covering identification, analysis, estimation, evaluation, and mitigation of risks "
            "throughout the AI system's lifecycle."
        ),
        "questions": [
            {"id": "q1", "text": "What risk assessment methodology did you use (e.g. ISO 31000, NIST AI RMF, internal framework)?"},
            {"id": "q2", "text": "Who is responsible for AI risk management (role and team)?"},
            {"id": "q3", "text": "What are the top three identified risks and how are they mitigated?"},
            {"id": "q4", "text": "How frequently is the risk register reviewed and updated?"},
            {"id": "q5", "text": "How are residual risks documented and communicated to decision-makers?"},
        ],
    },
    "art_10": {
        "title": "Article 10 — Data and Data Governance",
        "requirement": (
            "Training, validation, and test datasets must be subject to data governance practices "
            "covering design choices, collection, labelling, known biases, gaps, and mitigation measures."
        ),
        "questions": [
            {"id": "q1", "text": "Describe your training data sources, their size, and collection period."},
            {"id": "q2", "text": "What bias testing or fairness analysis was conducted on the training data?"},
            {"id": "q3", "text": "How was the data labelled and what quality controls are in place?"},
            {"id": "q4", "text": "What known gaps or limitations exist in the training data?"},
            {"id": "q5", "text": "Are there data consent mechanisms in place for personal data used in training?"},
        ],
    },
    "art_11": {
        "title": "Article 11 — Technical Documentation",
        "requirement": (
            "Technical documentation must be drawn up before the system is placed on the market "
            "and kept up to date. It must demonstrate compliance with the requirements of this Regulation."
        ),
        "questions": [
            {"id": "q1", "text": "Where is the technical documentation stored and who maintains it?"},
            {"id": "q2", "text": "Does it cover system architecture, training methodology, and performance metrics?"},
            {"id": "q3", "text": "When was the documentation last updated, and what triggered the update?"},
            {"id": "q4", "text": "Has the documentation been reviewed by legal, DPO, or compliance counsel?"},
            {"id": "q5", "text": "Can the documentation be produced to a market surveillance authority within 72 hours?"},
        ],
    },
    "art_17": {
        "title": "Article 17 — Quality Management System",
        "requirement": (
            "Providers must implement a quality management system covering strategy, design, "
            "development, testing, monitoring, post-market monitoring, and risk management for the AI system."
        ),
        "questions": [
            {"id": "q1", "text": "Do you hold a QMS certification (ISO 9001, ISO/IEC 42001, or equivalent)? If yes, provide the certificate reference."},
            {"id": "q2", "text": "What does the QMS specifically cover for this AI system's development and deployment lifecycle?"},
            {"id": "q3", "text": "When was the last internal or external QMS audit?"},
            {"id": "q4", "text": "How are non-conformities or incidents tracked and resolved within the QMS?"},
            {"id": "q5", "text": "How does the QMS integrate with post-market monitoring and incident reporting?"},
        ],
    },
    "art_25": {
        "title": "Article 25 — Deployer Obligations",
        "requirement": (
            "Deployers must use the AI system in accordance with instructions for use, assign human oversight "
            "to competent persons, and implement post-deployment monitoring proportionate to the risks."
        ),
        "questions": [
            {"id": "q1", "text": "Who are your deployers (internal teams or external organisations) and how were they onboarded?"},
            {"id": "q2", "text": "Describe the instructions for use provided to deployers — what format and what do they cover?"},
            {"id": "q3", "text": "What human oversight mechanisms are in place for deployers (review cadence, escalation path)?"},
            {"id": "q4", "text": "How do you monitor post-deployment performance and detect issues early?"},
            {"id": "q5", "text": "What is the process for deployers to report problems or suspend system use?"},
        ],
    },
    "art_27": {
        "title": "Article 27 — Fundamental Rights Impact Assessment (FRIA)",
        "requirement": (
            "Deployers of high-risk AI systems must carry out a FRIA prior to deployment, identifying "
            "which groups are likely to be affected, the risks to fundamental rights, and the measures "
            "taken to address those risks."
        ),
        "questions": [
            {"id": "q1", "text": "Who conducted the FRIA — internal team, external consultant, or DPO?"},
            {"id": "q2", "text": "Which population groups were identified as potentially affected by the system?"},
            {"id": "q3", "text": "What specific fundamental rights risks were identified (e.g. non-discrimination, privacy, due process)?"},
            {"id": "q4", "text": "What mitigations or safeguards were implemented in response to identified risks?"},
            {"id": "q5", "text": "When was the FRIA completed and when will it next be reviewed?"},
        ],
    },
    "art_30": {
        "title": "Article 30 — EU AI Database Registration",
        "requirement": (
            "Providers of high-risk AI systems must register in the EU AI public database before "
            "placing the system on the EU market or putting it into service."
        ),
        "questions": [
            {"id": "q1", "text": "What is your EU AI database registration number (EUAID)?"},
            {"id": "q2", "text": "When was the registration completed?"},
            {"id": "q3", "text": "Who is the named contact in the EU AI database for this system?"},
            {"id": "q4", "text": "Is the registration information kept current as the system is updated?"},
        ],
    },
    "art_33": {
        "title": "Article 33 — Conformity Assessment",
        "requirement": (
            "Providers must carry out a conformity assessment before placing the system on the market. "
            "For most Annex III systems this is internal (Annex VI); biometric systems require a "
            "third-party notified body (Annex VII)."
        ),
        "questions": [
            {"id": "q1", "text": "What type of conformity assessment was conducted — Annex VI (self-assessment) or Annex VII (third-party notified body)?"},
            {"id": "q2", "text": "Who performed the assessment (internal team, legal counsel, or notified body name)?"},
            {"id": "q3", "text": "What was the outcome? Was a certificate of conformity issued?"},
            {"id": "q4", "text": "What is the certificate or declaration reference number and date?"},
            {"id": "q5", "text": "How are material changes to the system handled — does a change trigger a new assessment?"},
        ],
    },
}


def get_article_questions(article_key: str) -> Dict:
    """Return question set for an article, or None if not supported."""
    return INTERVIEW_ARTICLES.get(article_key)


def list_interviewable_articles() -> List[str]:
    return list(INTERVIEW_ARTICLES.keys())
