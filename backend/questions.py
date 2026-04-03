"""
Pragma — Guided Context Questions
──────────────────────────────────
Category-specific questions that replace generic key/value context fields.

Each question has:
  key         — the context field name sent to the model
  label       — the question shown to the user
  type        — "text" | "select" | "multiselect" | "toggle"
  options     — list of choices (select / multiselect / toggle only)
  placeholder — hint text (text type only)
  required    — whether it must be answered before evaluating

VERSION is bumped whenever question ordering or content changes so that
ml/optimize_questions.py can track improvement across versions.
"""

VERSION = "1.0.0"

QUESTIONS: dict = {
    "hiring": [
        {
            "key": "role",
            "label": "What role is being filled?",
            "type": "text",
            "placeholder": "e.g. Software Engineer, Sales Manager",
            "required": True,
        },
        {
            "key": "criteria",
            "label": "What criteria are being used to evaluate candidates?",
            "type": "multiselect",
            "options": ["skills", "education", "experience", "personality", "culture fit", "demographics"],
            "required": True,
        },
        {
            "key": "demographics_in_data",
            "label": "Does the decision involve demographic information (age, gender, race, etc.)?",
            "type": "toggle",
            "options": ["yes", "no"],
            "required": True,
        },
        {
            "key": "candidate_background",
            "label": "Describe the candidate's background",
            "type": "text",
            "placeholder": "e.g. 5 years experience, career changer, Ivy League grad",
            "required": False,
        },
        {
            "key": "hiring_stage",
            "label": "What stage of hiring is this?",
            "type": "select",
            "options": ["resume screen", "phone screen", "interview", "final decision", "offer"],
            "required": False,
        },
    ],

    "workplace": [
        {
            "key": "decision_type",
            "label": "What type of workplace decision is this?",
            "type": "select",
            "options": ["promotion", "termination", "performance review", "accommodation request", "disciplinary action", "policy change"],
            "required": True,
        },
        {
            "key": "equal_application",
            "label": "Does this decision apply equally to all employees in similar situations?",
            "type": "toggle",
            "options": ["yes", "no", "unknown"],
            "required": True,
        },
        {
            "key": "affected_count",
            "label": "How many employees are affected?",
            "type": "select",
            "options": ["1", "2–10", "11–100", "100+"],
            "required": False,
        },
        {
            "key": "criteria",
            "label": "What criteria are driving this decision?",
            "type": "text",
            "placeholder": "e.g. missed targets, restructuring, complaint filed",
            "required": True,
        },
        {
            "key": "performance_metrics",
            "label": "Are objective performance metrics involved?",
            "type": "toggle",
            "options": ["yes", "no"],
            "required": False,
        },
    ],

    "finance": [
        {
            "key": "decision_type",
            "label": "What type of financial decision is this?",
            "type": "select",
            "options": ["loan approval", "credit limit", "insurance", "investment", "fraud flag", "account closure"],
            "required": True,
        },
        {
            "key": "data_inputs",
            "label": "What data inputs are being used?",
            "type": "multiselect",
            "options": ["credit score", "income", "employment status", "location / zip code", "payment history", "demographic data"],
            "required": True,
        },
        {
            "key": "location_factor",
            "label": "Does location or zip code factor into the decision?",
            "type": "toggle",
            "options": ["yes", "no"],
            "required": True,
        },
        {
            "key": "demographic_proxies",
            "label": "Could any inputs act as proxies for protected characteristics?",
            "type": "toggle",
            "options": ["yes", "no", "unknown"],
            "required": True,
        },
        {
            "key": "applicant_profile",
            "label": "Describe the applicant's financial profile",
            "type": "text",
            "placeholder": "e.g. credit score 620, income $55k, 3 missed payments",
            "required": False,
        },
    ],

    "healthcare": [
        {
            "key": "affected_party",
            "label": "Who is affected by this decision?",
            "type": "select",
            "options": ["individual patient", "patient population", "clinical staff", "institution"],
            "required": True,
        },
        {
            "key": "clinical_basis",
            "label": "What is the clinical or medical basis for this decision?",
            "type": "text",
            "placeholder": "e.g. diagnosis, treatment protocol, resource allocation",
            "required": True,
        },
        {
            "key": "resource_constraints",
            "label": "Are resource constraints (budget, capacity, staffing) driving this?",
            "type": "toggle",
            "options": ["yes", "no"],
            "required": True,
        },
        {
            "key": "consent",
            "label": "Has informed consent been obtained or considered?",
            "type": "toggle",
            "options": ["yes", "no", "not applicable"],
            "required": True,
        },
        {
            "key": "vulnerable_population",
            "label": "Does this involve a vulnerable or marginalized population?",
            "type": "toggle",
            "options": ["yes", "no"],
            "required": False,
        },
    ],

    "policy": [
        {
            "key": "affected_population",
            "label": "What population does this policy affect?",
            "type": "text",
            "placeholder": "e.g. all employees, residents in Zone 3, loan applicants",
            "required": True,
        },
        {
            "key": "primary_goal",
            "label": "What is the policy's primary goal?",
            "type": "text",
            "placeholder": "e.g. reduce costs, improve safety, increase efficiency",
            "required": True,
        },
        {
            "key": "disparate_impact",
            "label": "Could this policy disproportionately impact any specific group?",
            "type": "toggle",
            "options": ["yes", "no", "unknown"],
            "required": True,
        },
        {
            "key": "reversible",
            "label": "Is this policy reversible if harmful effects are observed?",
            "type": "toggle",
            "options": ["yes", "no"],
            "required": True,
        },
        {
            "key": "decision_authority",
            "label": "Who has decision-making authority here?",
            "type": "text",
            "placeholder": "e.g. board, department head, regulatory body",
            "required": False,
        },
    ],

    "personal": [
        {
            "key": "values_in_conflict",
            "label": "What values or interests are in conflict?",
            "type": "text",
            "placeholder": "e.g. loyalty vs honesty, career vs family, fairness vs loyalty",
            "required": True,
        },
        {
            "key": "others_affected",
            "label": "Who else is affected by this decision?",
            "type": "text",
            "placeholder": "e.g. partner, team, customers, community",
            "required": True,
        },
        {
            "key": "reversible",
            "label": "Is this decision reversible?",
            "type": "toggle",
            "options": ["yes", "no"],
            "required": True,
        },
        {
            "key": "stakes",
            "label": "How high are the stakes if this goes wrong?",
            "type": "select",
            "options": ["low", "medium", "high", "very high"],
            "required": True,
        },
        {
            "key": "public_test",
            "label": "Would you be comfortable if this decision were made public?",
            "type": "toggle",
            "options": ["yes", "no", "unsure"],
            "required": False,
        },
    ],

    "other": [],  # falls back to generic key/value fields in the frontend
}


def get_questions(category: str) -> list:
    """Return the question list for a given category."""
    return QUESTIONS.get(category, [])


def get_all() -> dict:
    """Return the full question bank with version metadata."""
    return {"version": VERSION, "questions": QUESTIONS}
