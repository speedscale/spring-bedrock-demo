#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f target/app.jar ]]; then
  ./scripts/build-app.sh
fi
if [[ -n "${AWS_PROFILE:-}" ]]; then
  exec python3 - "$@" <<'PY'
import json
import os
import subprocess
import sys

credentials = json.loads(subprocess.check_output([
    "aws", "configure", "export-credentials", "--profile", os.environ["AWS_PROFILE"], "--format", "process"
]))
env = dict(os.environ)
env["AWS_ACCESS_KEY_ID"] = credentials["AccessKeyId"]
env["AWS_SECRET_ACCESS_KEY"] = credentials["SecretAccessKey"]
env.pop("AWS_SESSION_TOKEN", None)
if credentials.get("SessionToken"):
    env["AWS_SESSION_TOKEN"] = credentials["SessionToken"]
os.execvpe("java", ["java", "-jar", "target/app.jar", *sys.argv[1:]], env)
PY
fi
exec java -jar target/app.jar "$@"
