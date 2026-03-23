# Ethical AI Decision Checker - Sample Use Cases

This directory contains sample test scenarios for validating the system.

## Use Case 1: Hiring Decision with Gender Bias

**Input**:
```json
{
  "decision": "Reject candidate for software engineer role",
  "context": {
    "experience_years": 5,
    "education": "Computer Science degree from tier-2 university",
    "gender": "female",
    "skills": ["Python", "JavaScript", "React"],
    "previous_titles": ["Junior Developer", "Mid-level Engineer"]
  }
}
```

**Expected Behavior**:
- Flag: `bias` (gender present in context)
- Flag: `fairness` (potential gender-based rejection)
- Kantian analysis should mention fairness violation
- Recommendation should suggest removing gender from evaluation

---

## Use Case 2: Loan Approval with Zip Code Discrimination

**Input**:
```json
{
  "decision": "Reject loan application for $50,000 home equity line of credit",
  "context": {
    "credit_score": 720,
    "annual_income": 85000,
    "employment_length_years": 12,
    "debt_to_income_ratio": 0.35,
    "zip_code": "90210"
  }
}
```

**Expected Behavior**:
- Flag: `bias` (zip_code present in context)
- Flag: `discrimination` (zip code used as rejection criterion)
- Utilitarian analysis should highlight harm to qualified applicant
- Recommendation should remove zip code from decision criteria

---

## Use Case 3: Fair Decision (No Major Risks)

**Input**:
```json
{
  "decision": "Approve promotion to team lead",
  "context": {
    "current_performance_rating": 4.8,
    "years_in_current_role": 3,
    "direct_reports_managed": 0,
    "skills_assessment": "excellent",
    "team_feedback": "highly collaborative"
  }
}
```

**Expected Behavior**:
- Minimal or no risk flags
- High confidence score (>0.8)
- Positive virtue ethics analysis
- Recommendation: proceed with promotion

---

## Use Case 4: Transparent vs. Opaque Decision

**Input** (Opaque):
```json
{
  "decision": "Deny health insurance coverage",
  "context": {
    "applicant_age": 42
  }
}
```

**Expected Behavior**:
- Flag: `transparency` (insufficient context)
- Flag: `bias` (age present)
- Recommendation should ask for explicit coverage denial reasons

---

## Running Test Cases

```bash
# Test with curl
curl -X POST http://localhost:8000/evaluate-decision \
  -H "Content-Type: application/json" \
  -d '{"decision":"Reject candidate","context":{"gender":"female","experience":5}}'

# Or run integration tests
pytest tests/test_api.py -v
```
