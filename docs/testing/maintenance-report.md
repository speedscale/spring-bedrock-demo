# Suite-maintenance validation

The expanded candidate passed twice with Java 21.0.12 and proxymock v2.5.1413 on November 18, 2026. Kiro Crew 0.12.2 executed the candidate assembly, negative control and both expanded runs through Kiro CLI 3.1.0. The capture, copy helper and native runner were prepared before that session. This is a Crew CLI rehearsal, with synthetic demo traffic.

| Native evidence | Original suite | Expanded suite, old mocks | Expanded A | Expanded B |
| --- | --- | --- | --- | --- |
| Result | PASS | FAIL (expected) | PASS | PASS |
| Inbound cases | 10 | 12 | 12 | 12 |
| Matching response statuses | 10/10 | 11/12 | 12/12 | 12/12 |
| Assertions passed | 40/40 | 46/48 | 48/48 | 48/48 |
| Bedrock HIT / MISS / PASSTHROUGH | 2 / 0 / 0 | 2 / 1 / 0 | 3 / 0 / 0 | 3 / 0 / 0 |
| OpenAPI operations | 2/2 | 2/2 | 2/2 | 2/2 |
| OpenAPI statuses | 3/5 | 4/5 | 3/5 | 3/5 |
| OpenAPI response fields | 4/7 | 5/7 | 4/7 | 4/7 |

The old mocks could not answer the new account-email question. Its recorded 200 became an observed 503, producing one native response-status mismatch and two failed assertions. The recorded successful body was preserved. More observed status coverage on that failing run comes from the error response; it does not establish correct behavior.

Both expanded runs had zero native status or body mismatches. The built-in `regression` test configuration evaluated status, Content-Type headers, response schema and response content type. The third Bedrock response answered the new question. STS remained unused with dummy local credentials, and passthrough was disabled. These replays made no live Bedrock calls.

All 13 original RRPair files are byte-identical to the base commit and to their copies in the candidate. The two new inbound cases and one outbound pair were copied additively, with UUIDs and SHA-256 hashes retained in the generated candidate's provenance. The [preserved-pair hashes](evidence/maintenance-baseline/preserved-pairs.json) establish baseline preservation. The original README and accepted recording were not replaced.

The application and OpenAPI contract were unchanged. Both passing expanded runs share the same fixture, JAR, contract and compiled test-config hashes. API 503 expectations remain unrecorded gaps. Additional input scenarios did not add new operations or response shapes. This evidence does not measure live model quality, performance under load, or all future application behavior.

## Native files

Each directory contains the native verdict, score, recorded and replayed coverage, compiled test config and command exits, plus the runner summary and fixture hashes. Local absolute path strings were made repository-relative for publication; result values were preserved.

- [Original suite](evidence/maintenance-baseline/summary.json)
- [Expanded suite with old mocks](evidence/maintenance-old-mocks/summary.json)
- [Expanded run A](evidence/maintenance-a/summary.json)
- [Expanded run B](evidence/maintenance-b/summary.json)

[Reproduce the workflow](suite-maintenance.md). [Prompt for Kiro Crew](crew-maintenance-prompt.md). Human review of the new expectations is still required before promoting the candidate.
