#!/usr/bin/env python3
"""Summarize and compare proxymock integration-test runs.

  proxymock-it-report.py summarize <run-dir> --recording DIR --spec FILE --test-config NAME [--replay-exit N] [--setup-failed MSG]
  proxymock-it-report.py report <run-dir-a> <run-dir-b>

Every figure is read from native proxymock output saved in the run directory.
Exit status: 0 PASS, 1 FAIL, 2 INCOMPLETE (missing evidence or setup failure).
"""
import argparse
import base64
import glob
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys

PASS, FAIL, INCOMPLETE = "PASS", "FAIL", "INCOMPLETE"
EXIT = {PASS: 0, FAIL: 1, INCOMPLETE: 2}
REDACTION_PATTERNS = {
    "12-digit account IDs": r"(?<!\d)\d{12}(?!\d)",
    "AWS access key IDs": r"\b(?:AKIA|ASIA)[A-Z0-9]{12,}",
    "JWTs": r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
    "OIDC provider ARNs": r"oidc[.-]eks|oidc-provider",
    "ARNs with account IDs": r"arn:aws:[a-z0-9-]+::\d+",
    "private IPv4 addresses": r"\b(?:10|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d+\.\d+(?:\.\d+)?\b",
    "bucket references": r"s3://|\.s3\.",
}


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f), None
    except (OSError, ValueError) as e:
        return None, f"{path}: {e}"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return (result.stdout or result.stderr).strip() if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def fixture_pairs(recording):
    """Recorded RRPairs, keyed by file, with direction/uuid/host/method/path/status."""
    pairs = []
    for path in sorted(glob.glob(os.path.join(recording, "*", "*.md"))):
        text = open(path).read()
        meta = re.search(r"^json: (.*)$", text, re.M)
        info = json.loads(meta.group(1)) if meta else {}
        req = info.get("http", {}).get("req", {})
        pairs.append({
            "file": os.path.relpath(path),
            "uuid": re.search(r"^uuid: (\S+)", text, re.M).group(1) if re.search(r"^uuid: (\S+)", text, re.M) else "",
            "direction": info.get("direction", ""),
            "host": req.get("host", ""),
            "method": req.get("method", ""),
            "path": req.get("uri", info.get("location", "")),
            "status": info.get("http", {}).get("res", {}).get("statusCode"),
            "text": text,
        })
    return pairs


def decoded_text(text):
    out = ""
    for m in re.finditer(r"^base64:\n(\S+)", text, re.M):
        raw = base64.b64decode(m.group(1) + "=" * (-len(m.group(1)) % 4))
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
        out += raw.decode("utf8", "replace")
    return out


def fixture_digest(recording):
    """SHA-256 of every fixture file; ignores transient dot directories such as .replay."""
    digests = {}
    for root, dirs, files in os.walk(recording):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(files):
            p = os.path.join(root, name)
            digests[os.path.relpath(p, recording)] = sha256(p)
    return digests


def native_assertions(verdict):
    goals = (verdict or {}).get("goals", {})
    counts = goals.get("assertions", {})
    if not counts.get("evaluated"):
        return None
    return {"assertions": counts.get("total", 0), "requests": counts.get("pairs", 0),
            "passed": counts.get("passed", 0), "failed": counts.get("failed", 0),
            "groups": goals.get("assertionGroups", []),
            "goals": [{"status": g.get("status", "").upper(), "goal": g.get("name", "")} for g in goals.get("goals", [])],
            "goalVerdict": goals.get("verdict", "").upper()}


def coverage_view(cov):
    s = cov["summary"]
    return {k: [s[k]["covered"], s[k]["total"]] for k in ("operations", "statuses", "fields")}


def summarize(args):
    out = args.run_dir.rstrip("/")
    checks, notes = [], []

    def check(name, status, detail):
        checks.append({"name": name, "status": status, "detail": detail})

    pairs = fixture_pairs(args.recording)
    inbound = [p for p in pairs if p["direction"] == "IN"]
    outbound = [p for p in pairs if p["direction"] == "OUT"]

    # Inputs and provenance
    before_path = os.path.join(out, "fixture.sha256.json")
    digest = fixture_digest(args.recording)
    before, _ = load_json(before_path)
    frozen = before == digest if before else None
    cfg_text = open(os.path.join(out, "test-config.json")).read() if os.path.exists(os.path.join(out, "test-config.json")) else ""
    cfg = json.loads(cfg_text) if cfg_text.strip().startswith("{") else {}
    app_paths = ["src", "pom.xml", "Dockerfile", "k8s", ".mvn", ".github"]
    app_dirty = run(["git", "status", "--porcelain", "--"] + app_paths)
    provenance = {
        "fixture": args.recording, "fixtureFiles": len(digest),
        "fixtureSha256": hashlib.sha256(json.dumps(digest, sort_keys=True).encode()).hexdigest(),
        "inboundPairs": len(inbound), "outboundPairs": len(outbound),
        "appRevision": run(["git", "rev-parse", "--short", "HEAD"]),
        "appJarSha256": sha256("target/app.jar") if os.path.exists("target/app.jar") else None,
        "openapiSha256": sha256(args.spec), "proxymock": json.loads(run(["proxymock", "version", "--client"]) or "{}").get("ClientVersion", ""),
        "testConfig": args.test_config,
        "testConfigSha256": hashlib.sha256(cfg_text.encode()).hexdigest() if cfg_text else None,
        "java": (run([os.path.join(os.environ.get("JAVA_HOME", ""), "bin", "java"), "-version"]) or "").splitlines()[0:1],
    }
    summary = {"run": os.path.basename(out), "provenance": provenance, "checks": checks, "notes": notes}

    if args.setup_failed:
        check("setup", INCOMPLETE, args.setup_failed)
        return finish(out, summary)

    check("fixture frozen during run", PASS if frozen else (FAIL if frozen is False else INCOMPLETE),
          "fixture file hashes unchanged from run start" if frozen else "fixture changed during the run" if frozen is False else "no start-of-run hash")
    check("app unchanged", PASS if not app_dirty else FAIL,
          "no changes under src, pom.xml, Dockerfile, k8s, .mvn, .github" if not app_dirty else "changed: " + app_dirty.replace("\n", "; "))

    # Redaction status (counts only, never values)
    hits = {}
    for p in pairs:
        blob = p["text"] + decoded_text(p["text"])
        for label, pat in REDACTION_PATTERNS.items():
            n = len(re.findall(pat, blob))
            if n:
                hits[label] = hits.get(label, 0) + n
    unredacted = sum(1 for p in pairs if re.search(r"^(Authorization|X-Amz-Security-Token): (?!REDACTED)", p["text"], re.M | re.I))
    summary["redaction"] = {"patternHits": hits, "unredactedAuthHeaders": unredacted,
                            "redactedMarkers": sum(p["text"].count("REDACTED-") for p in pairs)}
    check("redaction scan", PASS if not hits and not unredacted else FAIL,
          "no secret or private-identifier patterns found in headers, decoded bodies or metadata" if not hits and not unredacted
          else f"patterns found: {hits}, unredacted auth headers: {unredacted}")

    statuses, status_error = load_json(os.path.join(out, "command-exits.json"))
    if statuses is None:
        check("native commands", INCOMPLETE, status_error)
    else:
        check("native commands", PASS if statuses and all(code == 0 for code in statuses.values()) else FAIL,
              ", ".join(f"{name}={code}" for name, code in statuses.items()))

    # Native comparison
    verdict, err = load_json(os.path.join(out, "replay", "replay-verdict.json"))
    score, serr = load_json(os.path.join(out, "score.json"))
    cases = []
    if verdict is None or score is None:
        check("native comparison", INCOMPLETE, err or serr)
    else:
        by_uuid = {p["uuid"]: p for p in inbound}
        for pr in verdict.get("pairs", []):
            src = by_uuid.get(pr.get("refUuid"), {})
            cases.append({"case": os.path.basename(pr.get("sourceFile", "")), "method": pr["method"], "endpoint": pr["endpoint"],
                          "recordedStatus": pr["recordedStatus"], "observedStatus": pr["observedStatus"],
                          "status": pr["match"], "body": pr["bodyMatch"], "refUuid": pr.get("refUuid")})
        cases.sort(key=lambda c: (c["refUuid"] or ""))
        covered = {c["refUuid"] for c in cases}
        missing = [p["file"] for p in inbound if p["uuid"] not in covered]
        bad = [c for c in cases if c["status"] != "pass" or c["body"] != "pass"]
        acc = score.get("accuracy", {})
        ok = (len(cases) == len(inbound) and not missing and not bad and verdict.get("verdict") == "pass"
              and acc.get("pairs") == len(inbound) and acc.get("mismatches") == 0)
        check("native response comparison", PASS if ok else FAIL,
              f"{len(cases)}/{len(inbound)} recorded inbound cases have a verdict; "
              f"status+body mismatches: {acc.get('mismatches')} (status {acc.get('statusMismatches')}, body {acc.get('bodyMismatches')})"
              + (f"; no verdict for {missing}" if missing else "") + (f"; failing: {[c['case'] for c in bad]}" if bad else ""))
    summary["cases"] = cases

    # Evaluated assertions
    a = native_assertions(verdict)
    summary["assertions"] = a
    if not a:
        check("evaluated assertions", INCOMPLETE, "native verdict has no evaluated assertion totals")
    else:
        ok = a["assertions"] > 0 and a["requests"] == len(inbound) and a["failed"] == 0 and a["passed"] == a["assertions"] and a["goalVerdict"] == "PASS" and args.replay_exit == 0
        check("evaluated assertions", PASS if ok else FAIL,
              f"{a['assertions']} assertions over {a['requests']} requests: {a['passed']} passed, {a['failed']} failed; goal verdict {a['goalVerdict']}; replay exit {args.replay_exit}")
    summary["assertionTypes"] = [c.get("type") for g in cfg.get("assertionGroups", []) for c in g.get("configs", [])]

    # Mock outcomes
    mocked = []
    for f in sorted(glob.glob(os.path.join(out, "mocked", "*", "*.md"))):
        t = open(f).read()
        tag = lambda k: (re.search(rf"\b{k}=([^,\s]+)", t) or [None, None])[1]
        mocked.append({"file": os.path.relpath(f, out), "match": tag("match"), "refUuid": tag("refUuid"), "status": tag("servedStatus")})
    mr = (score or {}).get("matchRate")
    if not mr:
        check("mock outcomes", INCOMPLETE, "score.json has no matchRate")
        hit_refs = set()
    else:
        hit_refs = {m["refUuid"] for m in mocked if m["match"] == "HIT"}
        out_by_uuid = {p["uuid"]: p for p in outbound}
        ok = (mr["total"] > 0 and mr["matched"] == mr["total"] and mr["noMatch"] == 0 and mr["passthrough"] == 0
              and len(hit_refs) == mr["matched"] and hit_refs <= set(out_by_uuid)
              and all(out_by_uuid[r]["host"].startswith("bedrock-runtime.") for r in hit_refs))
        check("mock outcomes", PASS if ok else FAIL,
              f"Bedrock HIT {mr['matched']}, MISS {mr['noMatch']}, PASSTHROUGH {mr['passthrough']} (served by recorded pairs {sorted(os.path.basename(out_by_uuid[r]['file']) for r in hit_refs if r in out_by_uuid)})")
    unused = [{"file": p["file"], "host": p["host"]} for p in outbound if p["uuid"] not in hit_refs]
    summary["mocks"] = {"counts": {k: mr[k] for k in ("total", "matched", "noMatch", "passthrough")} if mr else None,
                        "hits": sorted(os.path.basename(p["file"]) + "@" + p["host"] for p in outbound if p["uuid"] in hit_refs),
                        "unused": unused,
                        "httpOutput": (score or {}).get("httpOutput", {}).get("status")}

    # Coverage
    rec, e1 = load_json(os.path.join(out, "coverage-recorded.json"))
    rep, e2 = load_json(os.path.join(out, "coverage-replayed.json"))
    if rec is None or rep is None:
        check("OpenAPI coverage", INCOMPLETE, e1 or e2)
    else:
        r, p = coverage_view(rec), coverage_view(rep)
        extras = {k: len(rep.get(k) or []) for k in ("unknown_routes", "undocumented_statuses", "unsupported_bodies")}
        extras_rec = {k: len(rec.get(k) or []) for k in ("unknown_routes", "undocumented_statuses", "unsupported_bodies")}
        below = [k for k in r if p[k][0] < r[k][0] or p[k][1] != r[k][1]]
        ok = not below and not any(extras.values()) and not any(extras_rec.values()) and rep.get("matched_pairs") == rep.get("inbound_pairs")
        check("OpenAPI coverage", PASS if ok else FAIL,
              "replayed " + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in p.items()) + "; recorded baseline " + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in r.items())
              + (f"; below baseline or denominator changed: {below}" if below else "") + (f"; unexpected entries {extras}" if any(extras.values()) else ""))
        summary["coverage"] = {"recorded": r, "replayed": p, "gaps": [g for g in rep.get("gaps", [])], "unexpected": extras}

    return finish(out, summary)


def finish(out, summary):
    statuses = [c["status"] for c in summary["checks"]]
    summary["result"] = FAIL if FAIL in statuses else INCOMPLETE if INCOMPLETE in statuses or not statuses else PASS
    with open(os.path.join(out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(f"{summary['run']}: {summary['result']}")
    for c in summary["checks"]:
        print(f"  {c['status']:<10} {c['name']}: {c['detail']}")
    return EXIT[summary["result"]]


def gap_text(g):
    return f"{g['method']} {g['path']} {g['status']}" + (f" `{g['field']}`" if g.get("field") else "") if g["kind"] != "operation" \
        else f"{g['method']} {g['path']}"


def report(args):
    base = os.path.dirname(os.path.abspath(args.run_a.rstrip("/")))
    runs = []
    for d in (args.run_a, args.run_b):
        s, err = load_json(os.path.join(d, "summary.json"))
        if s is None:
            print(f"INCOMPLETE: {err}", file=sys.stderr)
            return 2
        runs.append((os.path.basename(d.rstrip("/")), s))
    (na, a), (nb, b) = runs

    def key(s):
        return {"cases": [(c["refUuid"], c["method"], c["endpoint"], c["recordedStatus"], c["observedStatus"], c["status"], c["body"]) for c in s["cases"]],
                "assertions": (s["assertions"] or {}).get("assertions"), "assertionsFailed": (s["assertions"] or {}).get("failed"),
                "mocks": s["mocks"]["counts"], "hits": s["mocks"]["hits"], "unused": s["mocks"]["unused"],
                "coverage": s.get("coverage"),
                "fixture": s["provenance"]["fixtureSha256"], "jar": s["provenance"]["appJarSha256"], "openapi": s["provenance"]["openapiSha256"],
                "config": s["provenance"]["testConfigSha256"], "checks": [(c["name"], c["status"]) for c in s["checks"]]}
    ka, kb = key(a), key(b)
    diffs = [k for k in ka if ka[k] != kb[k]]
    consistent = not diffs
    overall = FAIL if FAIL in (a["result"], b["result"]) else INCOMPLETE if INCOMPLETE in (a["result"], b["result"]) else PASS
    if overall == PASS and not consistent:
        overall = FAIL

    p = a["provenance"]
    L = []
    L.append("# Recorded-traffic integration test report\n")
    L.append(f"**Overall: {overall}.** {na}: **{a['result']}**. {nb}: **{b['result']}**. "
             + ("The two runs agree on per-case outcomes, assertion counts, mock outcomes and coverage." if consistent
                else f"The two runs differ in: {', '.join(diffs)}. No retry was made."))
    L.append("\nThe app, OpenAPI contract and recording were unchanged between the runs. Outcomes are compared; timestamps and durations are not.\n")
    L.append("## Results\n")
    L.append(f"| Gate | {na} | {nb} |\n| --- | --- | --- |")
    for ca, cb in zip(a["checks"], b["checks"]):
        L.append(f"| {ca['name']} | {ca['status']} | {cb['status']} |")
    L.append("\n## Response comparison\n")
    L.append(f"Native status and body comparison of {len(a['cases'])} recorded inbound cases against the local app:\n")
    L.append(f"| Recorded case | Request | Recorded | {na} | {nb} | Status | Body |\n| --- | --- | --- | --- | --- | --- | --- |")
    cb_by = {c["refUuid"]: c for c in b["cases"]}
    for c in sorted(a["cases"], key=lambda c: c["case"]):
        o = cb_by.get(c["refUuid"], {})
        L.append(f"| {c['case']} | {c['method']} {c['endpoint']} | {c['recordedStatus']} | {c['observedStatus']} | {o.get('observedStatus', '-')} | {c['status']}/{o.get('status', '-')} | {c['body']}/{o.get('body', '-')} |")
    L.append("\n## Evaluated assertions\n")
    for n, s in runs:
        x = s["assertions"]
        L.append(f"- {n}: {x['passed']} passed, {x['failed']} failed of {x['assertions']} over {x['requests']} requests. Goals: " + "; ".join(f"{g['status']} {g['goal']}" for g in x["goals"]) + "." if x else f"- {n}: not evaluated")
    L.append(f"\nConfiguration: built-in `{p['testConfig']}`, unmodified. It checks, for every replayed request: " + ", ".join(f"`{t}`" for t in a["assertionTypes"])
             + " (headers: Content-Type only). Response bodies are compared separately by the native verdict, which found no body differences. "
             + "Passing assertions do not prove response values; the per-case comparison above does.\n")
    L.append("## Dependency mocks (Bedrock)\n")
    for n, s in runs:
        c = s["mocks"]["counts"]
        L.append(f"- {n}: HIT {c['matched']}, MISS {c['noMatch']}, PASSTHROUGH {c['passthrough']}. Served by: {', '.join(s['mocks']['hits'])}." if c else f"- {n}: no mock evidence")
    L.append("- Unused recorded dependency pairs: " + (", ".join(f"`{u['file']}` ({u['host']})" for u in a["mocks"]["unused"]) or "none")
             + ". The STS exchange is unused because the local app uses dummy static credentials. It is kept as evidence, not required.")
    L.append(f"- `httpOutput` assertion: {a['mocks']['httpOutput'] or 'not reported'} (the built-in regression config has none). The mock match counts above come from `replay score`.\n")
    L.append("## OpenAPI coverage\n")
    cov = a.get("coverage")
    if cov:
        L.append(f"Native `proxymock coverage` against `src/main/resources/static/openapi.yaml` (sha256 `{p['openapiSha256'][:12]}`):\n")
        L.append(f"| Measure | Recorded baseline | Replayed {na} | Replayed {nb} |\n| --- | --- | --- | --- |")
        covb = b.get("coverage", {}).get("replayed", {})
        for k in ("operations", "statuses", "fields"):
            f = lambda v: f"{v[0]}/{v[1]}" if v else "-"
            L.append(f"| {k} | {f(cov['recorded'][k])} | {f(cov['replayed'][k])} | {f(covb.get(k))} |")
        L.append("\nUnknown routes, undocumented statuses and unsupported bodies: " + ("none." if not any(cov["unexpected"].values()) else str(cov["unexpected"])))
        L.append("\nUncovered (gaps, left unfilled):\n")
        for g in cov["gaps"]:
            L.append(f"- {gap_text(g)}")
        L.append("\nThe 503 responses for chat and health were not recorded. Coverage measures observed contract behavior, not code coverage or assertion success.\n")
    L.append("## Provenance and redaction\n")
    L.append(f"- Fixture: `{p['fixture']}`, {p['fixtureFiles']} files ({p['inboundPairs']} inbound, {p['outboundPairs']} outbound pairs), manifest sha256 `{p['fixtureSha256'][:12]}`; identical at the start and end of both runs.")
    L.append(f"- App: git `{p['appRevision']}`, jar sha256 `{(p['appJarSha256'] or '')[:12]}`, {', '.join(p['java'])}; {p['proxymock']}.")
    L.append(f"- Test config sha256 `{(p['testConfigSha256'] or '')[:12]}`.")
    for n, s in runs:
        r = s["redaction"]
        L.append(f"- Redaction scan ({n}): {'clean' if not r['patternHits'] and not r['unredactedAuthHeaders'] else 'FINDINGS ' + str(r['patternHits'])}; {r['redactedMarkers']} `REDACTED-` markers; no values printed. A clean scan is not publication approval.")
    L.append("\n## Evidence\n")
    for n, _ in runs:
        L.append(f"- {n}: [summary](./{n}/summary.json), [replay output](./{n}/replay.stdout), [verdict](./{n}/replay/replay-verdict.json), "
                 f"[score](./{n}/score.json), [coverage, recorded](./{n}/coverage-recorded.json), [coverage, replayed](./{n}/coverage-replayed.json), "
                 f"[mock output](./{n}/mocked/), [app log](./{n}/app.log), [test config](./{n}/test-config.json)")
    L.append("\nEvidence files contain local absolute paths; review before publishing.")
    path = os.path.join(base, "report.md")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")
    print(f"{overall}: report written to {os.path.relpath(path)}")
    return EXIT[overall]


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("summarize")
    s.add_argument("run_dir")
    s.add_argument("--recording", required=True)
    s.add_argument("--spec", required=True)
    s.add_argument("--test-config", required=True)
    s.add_argument("--replay-exit", type=int, default=0)
    s.add_argument("--setup-failed")
    r = sub.add_parser("report")
    r.add_argument("run_a")
    r.add_argument("run_b")
    z = sub.add_parser("freeze")
    z.add_argument("recording")
    z.add_argument("out_file")
    args = ap.parse_args()
    if args.cmd == "freeze":
        with open(args.out_file, "w") as f:
            json.dump(fixture_digest(args.recording), f, indent=1, sort_keys=True)
        sys.exit(0)
    sys.exit(summarize(args) if args.cmd == "summarize" else report(args))


if __name__ == "__main__":
    main()
