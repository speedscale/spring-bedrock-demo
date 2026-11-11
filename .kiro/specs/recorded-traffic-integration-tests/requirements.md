# Integration testing from recorded traffic

Approved for implementation after review. Implement this bounded workflow without extending its scope.

## 1. Recorded inputs

Use the reviewed recording already present at `proxymock/recordings/support-chat/`. It contains 10 inbound cases, two Bedrock calls and one STS exchange captured on 2026-11-10. Its README documents capture-side DLP and the additional publication cleanup. Discovery and a second DLP application are unnecessary for this accepted fixture. Freeze it before either acceptance run. Use all its inbound API cases, including recorded validation errors. Derive expected counts from that input rather than hardcoding a previous snapshot's counts.

Do not invent requests, fabricate dependency responses, inject faults, or add cases to close coverage gaps. If a suitable capture is unavailable, stop with the missing prerequisite.

## 2. Redaction and repository contents

Capture-side DLP must redact credentials and sensitive fields before export to cloud or bucket storage. Verify a new capture after applying the policy; existing snapshots are not retroactively sanitized. Check authorization, cookies, AWS signing and security-token headers, STS form fields and XML credential responses, and embedded/encoded RRPair metadata. Preserve request relationships, types and nonsensitive behavior needed by replay. A publication review must also remove private account, bucket, cluster and deployment identifiers that credential DLP may leave intact.

The finished repository includes the reviewed spec, runner, reusable proxymock configuration, DLP policy and verified redacted RRPair fixtures under `proxymock/`. Do not blanket-ignore that directory. Ignore only disposable run output and logs. Keep credentials, raw pulls and private environment configuration outside the public checkout. Review the sanitized files before committing; redaction alone is not publication approval.

## 3. Mocked dependencies

Run the existing app locally with Java 21 under the proxymock JVM wrapper using the absolute Java binary directly (`proxymock mock ... -- /path/to/java -jar target/app.jar`), so proxy and TLS trust settings reach the Java process. Use recorded Bedrock responses and explicit `--no-passthrough`. Use dummy static AWS credentials, remove inherited real AWS credentials and IRSA/profile settings, and disable metadata credential lookup. The replay must not call live AWS services.

Report HIT, MISS and PASSTHROUGH counts from native evidence. Require exercised Bedrock calls to be HITs, with zero MISS and zero PASSTHROUGH. List unused dependency recordings separately. STS can be unused because dummy credentials avoid the IRSA exchange; do not force an STS call to satisfy an expectation.

## 4. Comparisons and assertions

Use native proxymock response status and body comparisons plus evaluated assertion totals from the native verdict JSON. Preserve nonzero exit codes from native scoring and coverage commands. A command exiting successfully or an assertion configuration merely being loaded does not establish a pass. Require a native verdict for every selected inbound pair, zero response mismatches, assertion evaluation enabled, a nonzero assertion total and zero failed assertions. Show what the evaluated assertions check. Begin with the native regression configuration; any necessary comparison exclusions must be narrow and explained before freezing the suite. Do not suppress meaningful body differences or skip failed pairs.

## 5. Measured schema coverage

Run native `proxymock coverage` against `src/main/resources/static/openapi.yaml` for both the recorded inbound traffic and replay results. Report covered/total operations, statuses and response fields, plus exact uncovered operations, statuses and field paths. Report unknown routes, undocumented statuses and unsupported bodies; unexpected entries fail the run. Native coverage must not fall below the recorded baseline. Do not infer coverage from source code, fabricate percentages or edit the contract to improve the numbers.

Report unrecorded 503 paths as gaps. Coverage measures observed contract behavior, independently of assertion success; it is not code coverage.

## 6. Repeatability and report

Run the full mock, replay, verdict and coverage sequence twice with the same app, recording, configuration, contract and environment. Use separate output directories. Both runs must satisfy the gates and agree on per-case outcomes, assertion counts, mock outcomes and coverage. Compare outcomes rather than timestamps or elapsed times. If they differ, report the difference and stop; do not retry until green.

Write a short, readable report containing both runs, the native comparison and assertion counts, mock counts, coverage fractions, uncovered paths, provenance and links to native evidence. Every result must be computed from saved outputs. Label PASS, FAIL or INCOMPLETE accurately. Missing evidence or setup failure cannot produce PASS. Show redaction status without printing secret values. Keep the report suitable for the opening shot after publication review.

## 7. Execution boundaries

Implement one small runner using the app's existing build/start commands and native proxymock outputs. Check Java 21, the required proxymock capabilities, the accepted fixture and free ports once. Use a local Java 21 selection without changing global settings. Do not invoke cloud or cluster commands for this offline suite. Reuse a build when inputs are unchanged. Use bounded startup and command timeouts, propagate failures, and clean up only processes started by this runner. Report a blocking prerequisite once and stop.

Keep the app, OpenAPI contract, Kubernetes deployments and global machine settings unchanged. Do not add generalized CLI subcommands, a reporting framework, synthetic failure demonstrations, coverage thresholds, CI work, README rewrites or extra implementation tasks. End after the two runs and report.
