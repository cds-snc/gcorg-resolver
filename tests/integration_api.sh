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
status=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
[[ "$status" == "200" ]]
echo "PASS  GET /health"

# POST /resolve - batch with known match, acronym match, and no-match
result=$(curl -sf -X POST "$BASE_URL/resolve" \
  -H 'Content-Type: application/json' \
  -d '{"names": ["Bibliothèque et Archives Canada", "CRA", "Department of Unicorns"]}')
[[ $(echo "$result" | jq '.results[0].gc_orgID') == 2262 ]]
[[ $(echo "$result" | jq '.results[1].gc_orgID') == 2303 ]]
[[ $(echo "$result" | jq '.results[2].matched') == false ]]
echo "PASS  POST /resolve"

# GET /resolve - plain text org ID
got=$(curl -sf "$BASE_URL/resolve?name=Agriculture")
[[ "$got" == "2222" ]]
echo "PASS  GET /resolve?name=Agriculture"

# GET /name - English
got=$(curl -sf "$BASE_URL/name?gc_orgID=2222&lang=en")
[[ "$got" == "Agriculture and Agri-Food Canada" ]]
echo "PASS  GET /name?gc_orgID=2222&lang=en"

# GET /name - French
got=$(curl -sf "$BASE_URL/name?gc_orgID=2222&lang=fr")
[[ "$got" == "Agriculture et Agroalimentaire Canada" ]]
echo "PASS  GET /name?gc_orgID=2222&lang=fr"

# GET /.well-known/security.txt - must return text/plain
content_type=$(curl -s -o /dev/null -w "%{content_type}" "$BASE_URL/.well-known/security.txt")
[[ "$content_type" == "text/plain" ]]
echo "PASS  GET /.well-known/security.txt"
