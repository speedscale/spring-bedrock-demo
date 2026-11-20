# Kiro Crew maintenance prompt

Extend this repository's recorded integration suite with the reviewed local additions in `proxymock/recordings/support-chat-local-additions`. Read `docs/testing/suite-maintenance.md` and inspect the new requests, responses and dependency calls. Work in this repository and use the native proxymock runner. Work alone without starting other agents or communicating externally.

Preserve every file in the accepted `proxymock/recordings/support-chat` recording. Keep application source, OpenAPI contract, test configuration and existing expectations unchanged. Build a new candidate under `proxymock/tmp/` using `scripts/extend-recording.py`. Stop on duplicate UUIDs or paths; report the conflict.

Run the complete candidate with only the original dependency mocks first. Explain the expected failure for the new support question using the native verdict and mock MISS evidence. Then use the expanded candidate mocks and run the complete suite twice. Keep passthrough disabled and use the runner's dummy AWS credentials. Use free ports and a new result directory for every run. Do not capture live traffic or call AWS during this task.

Report the native response comparisons, evaluated assertions, mock HIT/MISS/passthrough counts, fixture hashes and OpenAPI coverage. Distinguish additional scenarios from new schema coverage. If anything fails, investigate without rewriting expected responses. Show the candidate diff and stop for human review before promotion. Do not commit, push or publish.
