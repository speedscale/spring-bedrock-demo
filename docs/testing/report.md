# Recorded-traffic integration test report

**PASS: both unchanged runs agree.** Java 21, proxymock v2.5.1322.

| Result | Run 1 | Run 2 |
| --- | --- | --- |
| Status and body | 10/10 | 10/10 |
| Assertions | 40/40 | 40/40 |
| Bedrock HIT / MISS / PASSTHROUGH | 2 / 0 / 0 | 2 / 0 / 0 |
| OpenAPI operations | 2/2 | 2/2 |
| OpenAPI statuses | 3/5 | 3/5 |
| OpenAPI response fields | 4/7 | 4/7 |

All 10 recorded inbound requests were replayed. Assertions evaluated status, the Content-Type header, response schema and response content type. Native response comparison separately checked body values. Both recorded Bedrock calls were served locally, with passthrough disabled and dummy AWS credentials. The captured STS exchange was unused. No live Bedrock calls were made.

Native recorded and replayed coverage agree. Unknown routes, undocumented statuses and unsupported bodies: none. Unrecorded gaps remain unfilled:

- `GET /actuator/health` 503, including `$.groups` and `$.status`.
- `POST /api/chat` 503, including `$.error`.

[Run 1 verdict](evidence/released-1/verdict.json), [score](evidence/released-1/score.json), [coverage](evidence/released-1/coverage-replayed.json). [Run 2 verdict](evidence/released-2/verdict.json), [score](evidence/released-2/score.json), [coverage](evidence/released-2/coverage-replayed.json). The evidence directory also contains the recorded coverage, compiled test configuration and native command exit codes for each run.

The fixture, application jar, OpenAPI contract and test configuration hashes agree across runs. App source revision: `0990c42`; fixture manifest: `a3336adf8e5c512ebb864c8b53726a29e850baa2711fa6e07fe5ca5798cc5052`.

The [recording provenance](../../proxymock/recordings/support-chat/README.md) describes capture-side DLP and publication cleanup. This is demo traffic. Native evidence is retained; local path strings in score JSON are made repository-relative for publication. Generate full local evidence with the [runner](../../scripts/proxymock-it.sh).
