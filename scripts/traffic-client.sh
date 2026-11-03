#!/usr/bin/env bash
set -euo pipefail
base_url=http://localhost:8080
count=30
interval=2
timeout=35
output=
while (( $# )); do
  case "$1" in
    --base-url|--count|--interval|--timeout|--output)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 2; }
      case "$1" in
        --base-url) base_url=$2 ;; --count) count=$2 ;; --interval) interval=$2 ;;
        --timeout) timeout=$2 ;; --output) output=$2 ;;
      esac
      shift 2 ;;
    --help|-h)
      echo 'Usage: traffic-client.sh [--base-url URL] [--count 30] [--interval 2] [--timeout 35] [--output run.json]'
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
[[ "$count" =~ ^[1-9][0-9]*$ ]] || { echo '--count must be a positive integer' >&2; exit 2; }
[[ "$interval" =~ ^[0-9]+([.][0-9]+)?$ ]] || { echo '--interval must be nonnegative seconds' >&2; exit 2; }
[[ "$timeout" =~ ^[0-9]+([.][0-9]+)?$ && "$timeout" =~ [1-9] ]] || { echo '--timeout must be positive seconds' >&2; exit 2; }
run_id="bedrock-client-$(date -u +%Y%m%dT%H%M%SZ)-$$"
started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
attempted=0; passed=0; paid=0; ok=0; rejected=0; failed=0; failures='[]'
paid_limit=$(( count / 4 * 2 + (count % 4 < 2 ? count % 4 : 2) ))
printf 'Run %s: %s requests, at most %s paid chat attempts; no retries.\n' "$run_id" "$count" "$paid_limit"
for (( i=1; i<=count; i++ )); do
  if (( i > 1 )); then sleep "$interval"; fi
  method=POST; path=/api/chat; expected=200
  case $(( (i - 1) % 4 )) in
    0) name=password-reset; body='{"prompt":"How do I reset my password? Answer in one sentence."}' ;;
    1) name=account-access; body='{"prompt":"What should I do if I cannot sign in? Answer in one sentence."}' ;;
    2) name=blank-prompt; body='{"prompt":""}'; expected=400 ;;
    3) name=health; method=GET; path=/actuator/health; body= ;;
  esac
  attempted=$i
  if [[ "$method" == POST && "$expected" == 200 ]]; then paid=$(( paid + 1 )); fi
  args=(--silent --show-error --retry 0 --max-time "$timeout" --output /dev/null --write-out '%{http_code}'
        --request "$method" --header 'Content-Type: application/json' --header 'Accept: application/json'
        --header "X-Demo-Run: $run_id")
  if [[ "$method" == POST ]]; then args+=(--data "$body"); fi
  if status=$(curl "${args[@]}" "${base_url%/}$path"); then
    case "$status" in 200) ok=$(( ok + 1 )) ;; 400) rejected=$(( rejected + 1 )) ;; esac
    if [[ "$status" != "$expected" ]]; then
      printf -v failures '[{"request":%s,"case":"%s","error":"unexpected HTTP status","status":"%s"}]' "$i" "$name" "$status"
      failed=1
    fi
  else
    curl_exit=$?
    printf -v failures '[{"request":%s,"case":"%s","error":"curl failed","curl_exit":%s}]' "$i" "$name" "$curl_exit"
    failed=1
  fi
  printf '%s/%s %s: HTTP %s\n' "$i" "$count" "$name" "${status:-000}"
  if (( failed )); then break; fi
  passed=$(( passed + 1 ))
done
finished_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf -v summary '{"run_id":"%s","started_at":"%s","finished_at":"%s","requested":%s,"attempted":%s,"passed":%s,"bedrock_chat_attempts":%s,"statuses":{"200":%s,"400":%s},"failures":%s}' \
  "$run_id" "$started_at" "$finished_at" "$count" "$attempted" "$passed" "$paid" "$ok" "$rejected" "$failures"
if [[ -n "$output" ]]; then printf '%s\n' "$summary" > "$output"; fi
printf '%s\n' "$summary"
exit "$failed"
