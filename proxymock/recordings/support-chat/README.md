# Recorded Spring Bedrock traffic

Captured on 2026-11-10 through the Kubernetes Service: six health requests, two recorded validation responses, two successful chat requests, two Bedrock dependency calls and one IRSA STS call. These are observed cases, not generated responses.

Capture-side DLP redacted authorization, AWS session headers and STS credential/identity fields before Cloud and S3 export. The publication review also replaced the STS provider ARN, removed private network and request metadata, and changed cluster labels to `example`. Bodies are stored decompressed for inspection; API inputs, statuses and application response bodies are preserved. No bucket names, snapshot IDs, account IDs or credentials are needed for local replay.

Local replay uses dummy AWS credentials, so it mocks the two Bedrock calls and does not use the STS response. Keep the STS pair as evidence of the captured IRSA exchange; do not require a local STS call.

Native OpenAPI coverage is 2/2 operations, 3/5 statuses and 4/7 fields. Neither documented 503 response was captured. Report these gaps without inventing cases.

Review your own traffic before committing it. Enabling a DLP policy does not sanitize old snapshots. The example policy in `proxymock/dlprules/spring-bedrock-demo-capture.json` is scoped to the application namespace and service; it must be activated in the capture installation, not merely saved in this repository.
