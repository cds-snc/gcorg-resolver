#!/usr/bin/env bash
# Integration tests for the dev or prod API
# Runs after terraform apply

set -euo pipefail

if [[ -z "${BASE_URL:-}" ]]; then
  echo "BASE_URL is required"
  exit 1
fi

echo "Testing $BASE_URL"

# GET /health - just check it returns 200
echo "Testing /health endpoint..."
status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
[[ "$status" == "200" ]]
echo "PASS  GET /health"

# POST /resolve - batch with known match, acronym match, and no-match
echo "Testing /resolve POST endpoint..."
result=$(curl -sf -X POST "$BASE_URL/resolve" \
  -H 'Content-Type: application/json' \
  -d '{"names": ["Bibliothèque et Archives Canada", "CRA", "Department of Unicorns"]}')
[[ $(echo "$result" | jq '.results[0].gc_orgID') == 2262 ]]
[[ $(echo "$result" | jq '.results[1].gc_orgID') == 2303 ]]
[[ $(echo "$result" | jq '.results[2].matched') == false ]]
echo "PASS  POST /resolve"

# GET /resolve - plain text org ID
echo "Testing /resolve GET endpoint..."
got=$(curl -sf "$BASE_URL/resolve?name=Agriculture")
[[ "$got" == "2222" ]]
echo "PASS  GET /resolve?name=Agriculture"

# GET /name - English
echo "Testing /name GET endpoint (English)..."
got=$(curl -sf "$BASE_URL/name?gc_orgID=2222&lang=en")
[[ "$got" == "Agriculture and Agri-Food Canada" ]]
echo "PASS  GET /name?gc_orgID=2222&lang=en"

# GET /name - French
echo "Testing /name GET endpoint (French)..."
got=$(curl -sf "$BASE_URL/name?gc_orgID=2222&lang=fr")
[[ "$got" == "Agriculture et Agroalimentaire Canada" ]]
echo "PASS  GET /name?gc_orgID=2222&lang=fr"

# GET /.well-known/security.txt - must return something STARTING with text/plain
echo "Testing /.well-known/security.txt endpoint..."
content_type=$(curl -s -o /dev/null -w "%{content_type}" "$BASE_URL/.well-known/security.txt")
[[ "$content_type" == text/plain* ]]
echo "PASS  GET /.well-known/security.txt"

# GET /name?field=abbreviation - proves gc_org_info.csv is in the Lambda bundle
echo "Testing /name GET endpoint (field=abbreviation, English)..."
got=$(curl -sf "$BASE_URL/name?gc_orgID=2222&lang=en&field=abbreviation")
[[ "$got" == "AAFC" ]]
echo "PASS  GET /name?gc_orgID=2222&lang=en&field=abbreviation"

echo "Testing /name GET endpoint (field=abbreviation, French)..."
got=$(curl -sf "$BASE_URL/name?gc_orgID=2222&lang=fr&field=abbreviation")
[[ "$got" == "AAC" ]]
echo "PASS  GET /name?gc_orgID=2222&lang=fr&field=abbreviation"

# GET /name?field=legal_title
echo "Testing /name GET endpoint (field=legal_title, English)..."
got=$(curl -sf "$BASE_URL/name?gc_orgID=2222&lang=en&field=legal_title")
[[ "$got" == "Department of Agriculture and Agri-Food" ]]
echo "PASS  GET /name?gc_orgID=2222&lang=en&field=legal_title"

echo "Testing /name GET endpoint (field=legal_title, French)..."
got=$(curl -sf "$BASE_URL/name?gc_orgID=2222&lang=fr&field=legal_title")
[[ "$got" == "Ministère de l’Agriculture et de l’Agroalimentaire" ]]
echo "PASS  GET /name?gc_orgID=2222&lang=fr&field=legal_title"

# Org with no abbreviation on record should return 200 with empty body
echo "Testing /name GET endpoint (empty abbreviation returns 200)..."
http_code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/name?gc_orgID=2270&lang=en&field=abbreviation")
[[ "$http_code" == "200" ]]
echo "PASS  GET /name?gc_orgID=2270&lang=en&field=abbreviation (empty, 200)"

# Unrecognised field returns 400
echo "Testing /name GET endpoint (bad field returns 400)..."
http_code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/name?gc_orgID=2222&lang=en&field=abbrevation")
[[ "$http_code" == "400" ]]
echo "PASS  GET /name?gc_orgID=2222&lang=en&field=abbrevation (400)"
