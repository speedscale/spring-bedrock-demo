#!/usr/bin/env bash
# Offline integration test: replay the recorded inbound API cases against the
# local app, with the recorded Bedrock responses served by proxymock mocks.
#
#   scripts/proxymock-it.sh <run-name>
#
# Evidence is written to proxymock/results/<run-name>/ and summarized by
# scripts/proxymock-it-report.py. The exit status is the run's verdict.
set -euo pipefail
cd "$(dirname "$0")/.."

run="${1:?usage: scripts/proxymock-it.sh <run-name>}"
[[ "$run" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "run name must match [A-Za-z0-9._-]+" >&2; exit 2; }

recording=proxymock/recordings/support-chat
spec=src/main/resources/static/openapi.yaml
test_config="${PROXYMOCK_IT_TEST_CONFIG:-regression}"
app_port=8080
startup_limit=120
out="proxymock/results/$run"

fail() { echo "BLOCKED: $*" >&2; exit 2; }

# --- Preflight: Java 21, proxymock capabilities, fixture, ports -------------
java21="${JAVA21_HOME:-/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home}"
[[ -x "$java21/bin/java" ]] || fail "Java 21 not found at $java21 (set JAVA21_HOME)"
java_version=$("$java21/bin/java" -version 2>&1)
grep -q '"21\.' <<< "$java_version" || fail "$java21 is not Java 21"
command -v proxymock >/dev/null || fail "proxymock is not on PATH"
for tool in python3 curl lsof; do command -v "$tool" >/dev/null || fail "$tool is required"; done
proxymock coverage --help >/dev/null 2>&1 || fail "proxymock lacks 'coverage'"
proxymock replay score --help >/dev/null 2>&1 || fail "proxymock lacks 'replay score'"
mock_help=$(proxymock mock --help 2>&1)
[[ "$mock_help" == *"--no-passthrough"* ]] || fail "proxymock mock lacks --no-passthrough"
[[ -d "$recording" ]] || fail "accepted recording missing: $recording"
[[ -f "$spec" ]] || fail "OpenAPI contract missing: $spec"
[[ ! -e "$out" ]] || fail "$out already exists; use a new run name"
for port in "$app_port" 4140; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then fail "port $port is already in use"; fi
done

# --- Build only when the jar is missing or older than its inputs ------------
export JAVA_HOME="$java21"
if [[ ! -f target/app.jar || -n "$(find pom.xml src -type f -newer target/app.jar -print -quit)" ]]; then
  PATH="$java21/bin:$PATH" scripts/build-app.sh
fi

mkdir -p "$out"
python3 scripts/proxymock-it-report.py freeze "$recording" "$out/fixture.sha256.json"
config_status=0
proxymock test-config compile "$test_config" >"$out/test-config.json" 2>"$out/test-config.stderr" || config_status=$?
mock_pid=""
cleanup() {
  if [[ -n "$mock_pid" ]] && kill -0 "$mock_pid" 2>/dev/null; then
    kill -INT "$mock_pid" 2>/dev/null || true
    for _ in $(seq 1 30); do kill -0 "$mock_pid" 2>/dev/null || break; sleep 1; done
    kill -0 "$mock_pid" 2>/dev/null && { pkill -TERM -P "$mock_pid" 2>/dev/null || true; kill -TERM "$mock_pid" 2>/dev/null || true; sleep 2; }
    kill -0 "$mock_pid" 2>/dev/null && { pkill -KILL -P "$mock_pid" 2>/dev/null || true; kill -KILL "$mock_pid" 2>/dev/null || true; }
  fi
  mock_pid=""
}
trap cleanup EXIT

# --- Start the app under the proxymock JVM wrapper, offline -----------------
# A clean environment keeps real AWS credentials, profiles and IRSA settings
# out of the JVM. Dummy static credentials let the SDK sign requests that the
# mock answers; metadata credential lookup is disabled.
clean_env=(env -i HOME="$HOME" PATH="$PATH" TMPDIR="${TMPDIR:-/tmp}" USER="${USER:-}" LANG=en_US.UTF-8
  JAVA_HOME="$java21" PORT="$app_port" AWS_REGION=us-east-1
  AWS_ACCESS_KEY_ID=dummy-access-key AWS_SECRET_ACCESS_KEY=dummy-secret-key
  AWS_EC2_METADATA_DISABLED=true)

"${clean_env[@]}" proxymock mock \
  --in "$recording" --out "$out/mocked" --no-passthrough \
  --log-to "$out/mock.log" --app-log-to "$out/app.log" --timeout 10m \
  -- "$java21/bin/java" -jar target/app.jar >"$out/mock.stdout" 2>&1 &
mock_pid=$!

ready=0
for _ in $(seq 1 "$startup_limit"); do
  kill -0 "$mock_pid" 2>/dev/null || break
  if curl --connect-timeout 1 --max-time 2 -fsS -o /dev/null "http://localhost:$app_port/actuator/health" 2>/dev/null; then ready=1; break; fi
  sleep 1
done
if [[ "$ready" != 1 ]]; then
  echo "app did not become ready within ${startup_limit}s; see $out/mock.log and $out/app.log" >&2
  cleanup
  setup_status=0
  python3 scripts/proxymock-it-report.py summarize "$out" --recording "$recording" --spec "$spec" --test-config "$test_config" --setup-failed "app did not become ready" || setup_status=$?
  exit "$setup_status"
fi

# --- Replay the recorded inbound cases --------------------------------------
replay_status=0
proxymock replay \
  --in "$recording" --test-against "http://localhost:$app_port" \
  --test-config "$test_config" --mocks-out "$out/mocked" --out "$out/replay" \
  --timeout 5m >"$out/replay.stdout" 2>&1 || replay_status=$?

cleanup   # flush mock output before scoring

# --- Native scoring and coverage --------------------------------------------
score_status=0
recorded_status=0
replayed_status=0
proxymock replay score "$out/replay" --mock-run "$out/mocked" --mocks-out "$out/mocked" -o json >"$out/score.json" 2>"$out/score.stderr" || score_status=$?
proxymock coverage --spec "$spec" --in "$recording" --json >"$out/coverage-recorded.json" 2>"$out/coverage-recorded.stderr" || recorded_status=$?
proxymock coverage --spec "$spec" --in "$out/replay" --json >"$out/coverage-replayed.json" 2>"$out/coverage-replayed.stderr" || replayed_status=$?

printf '{"testConfig":%s,"score":%s,"coverageRecorded":%s,"coverageReplayed":%s}\n' "$config_status" "$score_status" "$recorded_status" "$replayed_status" >"$out/command-exits.json"

python3 scripts/proxymock-it-report.py summarize "$out" --recording "$recording" --spec "$spec" \
  --test-config "$test_config" --replay-exit "$replay_status"
