# Tasks: Bedrock Chat API Baseline

This folder documents existing behavior. It queues no implementation work and has no retrospective checked boxes.

For a new app feature, create a focused feature spec. For API-contract enforcement, use `../openapi-contract-first/tasks.md`.

## Verification reference

- Run `./mvnw -B -ntp verify` for local HTTP integration tests without AWS.
- Use the existing CI workflow for OpenAPI validation, Kubernetes rendering, and container build checks.
- Use the API client Job in `k8s/api-client/job.yaml` for captured demo traffic through the Kubernetes Service. Follow the README commands to create it and check its logs and completion.
- Use `scripts/smoke-test.sh [base_url]` for an authorized live run; it makes one paid Bedrock call.
- Verify private IRSA, deployment health, capture, and S3 delivery separately when changing infrastructure.

Record the command, result, and relevant revision when claiming verification. Source inspection or the existence of code does not establish that a check passed.
