#!/usr/bin/env python3
"""Generate a finite, sequential mix of chat, validation and health requests."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4


CASES = (
    ("password-reset", "POST", "/api/chat", {"prompt": "How do I reset my password? Answer in one sentence."}, 200, "response"),
    ("account-access", "POST", "/api/chat", {"prompt": "What should I do if I cannot sign in? Answer in one sentence."}, 200, "response"),
    ("blank-prompt", "POST", "/api/chat", {"prompt": ""}, 400, "error"),
    ("health", "GET", "/actuator/health", None, 200, "status"),
)


def timestamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run(base_url, count, interval, timeout, run_id):
    summary = {"run_id": run_id, "started_at": timestamp(), "requested": count,
               "attempted": 0, "passed": 0, "bedrock_chat_attempts": 0, "statuses": {}, "failures": []}
    statuses = Counter()
    for index in range(count):
        if index:
            time.sleep(interval)
        name, method, path, body, expected, field = CASES[index % len(CASES)]
        request = Request(base_url.rstrip("/") + path, method=method,
                          data=json.dumps(body).encode() if body is not None else None,
                          headers={"Content-Type": "application/json", "X-Demo-Run": run_id})
        summary["attempted"] += 1
        if method == "POST" and expected == 200:
            summary["bedrock_chat_attempts"] += 1
        try:
            try:
                response = urlopen(request, timeout=timeout)
            except HTTPError as error:
                response = error
            with response:
                status = response.status
                statuses[str(status)] += 1
                content_type = response.headers.get("Content-Type", "")
                payload = json.loads(response.read())
            if status != expected:
                raise ValueError(f"expected HTTP {expected}, got {status}")
            media_type = content_type.partition(";")[0].strip().lower()
            if media_type != "application/json" and not media_type.endswith("+json"):
                raise ValueError("expected a JSON content type")
            if not isinstance(payload, dict) or not isinstance(payload.get(field), str) or not payload[field].strip():
                raise ValueError(f"expected a nonblank {field} string")
            if field == "status" and payload[field] != "UP":
                raise ValueError("application is not UP")
        except (URLError, OSError, ValueError) as error:
            summary["failures"].append({"request": index + 1, "case": name, "error": str(error)})
            print(f"{index + 1}/{count} {name}: FAILED ({error})", flush=True)
            break
        summary["passed"] += 1
        print(f"{index + 1}/{count} {name}: HTTP {status}", flush=True)
    summary["finished_at"] = timestamp()
    summary["statuses"] = dict(statuses)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--count", type=int, default=30, help="total requests, including free validation and health checks (default: 30)")
    parser.add_argument("--interval", type=float, default=2, help="seconds between requests (default: 2)")
    parser.add_argument("--timeout", type=float, default=35, help="timeout per request in seconds (default: 35)")
    parser.add_argument("--output", type=Path, help="save the run summary as JSON")
    args = parser.parse_args(argv)
    if args.count < 1:
        parser.error("--count must be positive")
    if not math.isfinite(args.interval) or args.interval < 0:
        parser.error("--interval must be finite and nonnegative")
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")
    run_id = "bedrock-client-" + uuid4().hex[:12]
    paid = sum(CASES[index % len(CASES)][4] == 200 and CASES[index % len(CASES)][1] == "POST" for index in range(args.count))
    print(f"Run {run_id}: {args.count} requests, at most {paid} paid Bedrock chat calls; no retries.", flush=True)
    summary = run(args.base_url, args.count, args.interval, args.timeout, run_id)
    text = json.dumps(summary, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text, end="")
    return 1 if summary["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
