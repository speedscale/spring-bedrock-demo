# Requirements: Bedrock Chat API

## Purpose and status

This is the baseline for the existing demo, derived from application source at commit `44ecc28`. It explains what to preserve when adding a feature. It is not a completed implementation plan or evidence that every behavior has been tested.

The app is one Java 21 Spring Boot backend with one cloud dependency, Amazon Bedrock. There is no console, RAG, database, conversation history, or streaming. The starting repository has no proxymock installation or recordings; adding those remains a live demo step.

## 1. Answer a question

As an API client, I can send a support question and receive an answer.

1. `POST /api/chat` accepts JSON containing only a string `prompt`.
2. For valid input, the service makes one `ChatModel.call` with the fixed support-assistant system message and the user's prompt. Each request is independent.
3. Success returns HTTP 200 with exactly `{"response":"<nonblank model text>"}`.

## 2. Reject invalid input and handle dependency failures

As a client, I receive predictable errors without upstream details.

1. Missing, null, empty, blank, non-string, oversized, malformed, and unknown input returns HTTP 400 before the model is called.
2. The current implementation uses `@NotBlank` and `@Size(max = 4000)`. Java string length counts UTF-16 code units. Exact Unicode conformance with the OpenAPI contract is pending work in the companion spec; do not claim these rules are already identical.
3. Validation errors return `{"error":"Request must contain only a prompt with 1 to 4000 nonblank characters."}`.
4. Model exceptions or missing/blank model output return HTTP 503 with `{"error":"Bedrock is unavailable. Retry later."}`. Logs include a fixed warning and the cause's simple class name, without upstream exception text.
5. Configuration sets the Bedrock timeout to 30 seconds and Spring AI retry attempts to one. Existing mocked tests do not establish an end-to-end timeout bound or the AWS SDK's underlying network-attempt count.

## 3. Run locally and in Kubernetes

As a developer, I can build the same app for local use and a private cluster.

1. `PORT`, `AWS_REGION`, and `BEDROCK_MODEL_ID` configure the app. Defaults are 8080, `us-east-1`, and `us.anthropic.claude-sonnet-5-5`.
2. AWS authentication uses the SDK credential chain. Local profile export is temporary. EKS deployment uses IRSA through private deployment configuration, with renewable role credentials.
3. The public Kubernetes base is a template: one replica, ClusterIP service, resource limits, a non-root container, and health probes. Its current `bedrock-credentials` Secret reference is a fallback template, not the authentication setup of the private EKS deployment.
4. Private IRSA configuration replaces that Secret reference and supplies the service account and web-identity configuration. Accounts, roles, cluster names, buckets, tenant configuration, credentials, and sealed-secret manifests stay outside the public repository.
5. Speedscale capture and AWS S3 BYOC are configured privately. Adding proxymock live must not require publishing captured private data.
6. There is no public ingress or application authentication. Demo access uses port-forwarding or a privately configured authenticated entry point.

## 4. Publish and verify the API

As a maintainer, I can inspect the contract and test without paying for model calls.

1. `GET /openapi.yaml` serves the checked-in OpenAPI 3.0.3 document.
2. Health, liveness, and readiness endpoints report application health without calling Bedrock.
3. `./mvnw -B -ntp verify` runs HTTP integration tests with a mocked `ChatModel` and no AWS access.
4. CI checks shell syntax, runs Maven verification, validates OpenAPI, renders the Kubernetes base, and builds the container. Deployment remains manual.
5. The real smoke test makes a paid Bedrock call. Mocked integration tests do not prove that live AWS credentials, model access, traffic capture, or deployment work.
6. The companion `openapi-contract-first` spec describes proposed improvements to contract enforcement. Those improvements are not installed by these documents.
