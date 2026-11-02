#!/usr/bin/env bash
set -euo pipefail
base_url="${1:-http://localhost:8080}"
curl --fail --silent --show-error "$base_url/actuator/health" |
  python3 -c 'import json,sys; assert json.load(sys.stdin)["status"] == "UP"; print("health: UP")'
curl --fail --silent --show-error "$base_url/openapi.yaml" |
  python3 -c 'import sys; assert sys.stdin.read().startswith("openapi: 3.0.3"); print("OpenAPI: available")'
curl --fail --silent --show-error --max-time 60 "$base_url/api/chat"   -H 'Content-Type: application/json' -d '{"prompt":"Explain what an API is in one short sentence."}' |
  python3 -c 'import json,sys; d=json.load(sys.stdin); assert isinstance(d["response"],str) and d["response"].strip(); print("chat:",d["response"])'
status=$(curl --silent --show-error -o /dev/null -w '%{http_code}' "$base_url/api/chat"   -H 'Content-Type: application/json' -d '{"prompt":""}')
[[ "$status" == 400 ]] || { echo "Expected 400 for blank prompt, got $status" >&2; exit 1; }
echo 'validation: 400'
