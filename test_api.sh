#!/bin/bash

# Ethical AI Decision Checker - Interactive Test Script
# Usage: ./test_api.sh

BASE_URL="http://localhost:8000"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     🧪 ETHICAL AI DECISION CHECKER - INTERACTIVE TEST SUITE   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Test 1: Health Check
echo "Test 1️⃣  - Health Check"
echo "─────────────────────────"
curl -s -X GET "$BASE_URL/health-check" | jq .
echo ""

# Test 2: Hiring Bias
echo "Test 2️⃣  - Hiring Bias Detection (Gender)"
echo "────────────────────────────────────────"
curl -s -X POST "$BASE_URL/evaluate-decision" \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "Reject job candidate for senior engineer position",
    "context": {
      "years_experience": 8,
      "education": "Bootcamp",
      "gender": "female",
      "github_repos": 15,
      "certifications": "AWS, Kubernetes"
    }
  }' | jq '.risk_flags, .confidence_score, .recommendation'
echo ""

# Test 3: Loan Discrimination
echo "Test 3️⃣  - Loan Discrimination (Zip Code)"
echo "────────────────────────────────────────"
curl -s -X POST "$BASE_URL/evaluate-decision" \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "Deny home equity line of credit application",
    "context": {
      "credit_score": 750,
      "annual_income": 120000,
      "employment_years": 10,
      "debt_to_income": 0.25,
      "zip_code": "90210"
    }
  }' | jq '.risk_flags, .confidence_score, .recommendation'
echo ""

# Test 4: Fair Promotion Decision
echo "Test 4️⃣  - Fair Decision (Promotion)"
echo "────────────────────────────────────"
curl -s -X POST "$BASE_URL/evaluate-decision" \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "Approve promotion to team lead",
    "context": {
      "performance_rating": 4.8,
      "years_in_role": 3,
      "team_feedback": "exceptional leadership",
      "projects_led": 5,
      "on_time_delivery": "100%"
    }
  }' | jq '.risk_flags, .confidence_score, .recommendation'
echo ""

# Test 5: Age Discrimination
echo "Test 5️⃣  - Age Discrimination Detection"
echo "─────────────────────────────────────"
curl -s -X POST "$BASE_URL/evaluate-decision" \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "Reject applicant due to overqualification",
    "context": {
      "age": 58,
      "years_experience": 30,
      "education": "MBA",
      "salary_requirement": "market_rate"
    }
  }' | jq '.risk_flags, .confidence_score, .recommendation'
echo ""

# Test 6: Full Response Example
echo "Test 6️⃣  - Full Response Example"
echo "──────────────────────────────"
curl -s -X POST "$BASE_URL/evaluate-decision" \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "Reject loan application",
    "context": {
      "credit_score": 650,
      "race": "Hispanic",
      "zip_code": "60617"
    }
  }' | jq '.'
echo ""

echo "═════════════════════════════════════════════════════════════════"
echo "✅ All tests completed!"
echo "═════════════════════════════════════════════════════════════════"
