# Spring Bedrock Demo

A Java 21 Spring Boot API that sends support questions to Amazon Bedrock Converse. Forked from [AWS's Spring AI Bedrock sample](https://github.com/aws-samples/sample-springai-amazonbedrock), with the interactive console, temperature examples, and RAG removed. One process, one cloud dependency, no database.

## Architecture

Example deployment and demo workflow. The S3 collector follows the [documented BYOC installation](https://docs.speedscale.com/byoc/configure-kubernetes/#amazon-s3-with-eks-iam-roles-for-service-accounts) in namespace `byoc-s3`. IRSA, capture and storage settings belong in a private overlay.

### Application architecture

![API traffic generator, Kubernetes Service and Spring Boot API in EKS calling Bedrock Sonnet 5.5 and STS](docs/architecture/application.svg)

### Capture and storage

![Speedscale capture routed through Kubernetes namespaces to S3 and Speedscale Cloud](docs/architecture/capture-storage.svg)

### Local testing in Kiro

![Pull an S3 snapshot into Kiro, mock AWS calls, replay tests, and check assertions and OpenAPI schema coverage](docs/architecture/local-testing.svg)

[Mermaid sources and rendering instructions](docs/architecture/README.md).

## Recorded-traffic integration tests

See the [finished report](docs/testing/report.md). Review the [approved spec](.kiro/specs/recorded-traffic-integration-tests/spec.md) and [redacted recording](proxymock/recordings/support-chat/README.md). The suite starts this app locally with recorded Bedrock responses, compares every recorded API response, evaluates native assertions and measures native OpenAPI coverage. Local replay needs no AWS access and makes no paid model calls. STS is unused with dummy local credentials.

Install proxymock, Java 21, Python 3, curl and lsof. Set `JAVA21_HOME` to your JDK 21 directory if it is not the Homebrew installation. From the repository root, use a new name for each run:

```bash
./scripts/proxymock-it.sh run-1
./scripts/proxymock-it.sh run-2
python3 scripts/proxymock-it-report.py report proxymock/results/run-1 proxymock/results/run-2
```

Evidence is saved separately under `proxymock/results/<run-name>/`. Keep the inputs unchanged between runs. Only recorded cases run: the documented 503 paths remain coverage gaps. The fixtures, DLP policy and reusable test assets belong in Git; generated results and caches are ignored. Raw captures and private deployment settings stay outside this repository.

The saved suite was validated twice with Java 21 and released proxymock `v2.5.1322`. It uses the built-in `regression` test configuration and launches the Java binary directly under the proxymock wrapper.

## Run locally

Install JDK 21 and configure AWS credentials with access to Bedrock. The application uses the AWS SDK default credential chain. When `AWS_PROFILE` is set, the launcher uses AWS CLI v2 and Python 3 to export that profile's current credentials into the JVM environment without writing them to disk.

```bash
export AWS_PROFILE=your-profile
./scripts/build-app.sh
./scripts/run-app.sh
```

Set `JAVA_HOME` to your JDK 21 installation. The API listens on port 8080. Override `PORT`, `AWS_REGION`, or `BEDROCK_MODEL_ID` as needed. The defaults are `us-east-1` and `us.anthropic.claude-sonnet-5-5`; the model must be available in your account. Each successful chat request makes a paid Bedrock call.

```bash
curl --fail http://localhost:8080/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"How do I reset my password?"}'
./scripts/smoke-test.sh
```

Successful calls return `{"response":"..."}`. Invalid requests return HTTP 400; Bedrock failures or empty model responses return HTTP 503 with `{"error":"..."}`. Requests accept only a nonblank `prompt`, up to 4000 characters. Each request is independent, with no conversation history or streaming.

## Generate demo traffic in Kubernetes

With the app deployed and kubectl pointed at your demo cluster, run the [API client Job](k8s/api-client/job.yaml). It calls the Kubernetes Service at `http://spring-bedrock-demo.spring-bedrock-demo.svc.cluster.local:8080`, so captured requests use the Service hostname.

```bash
job=$(kubectl create -f k8s/api-client/job.yaml -o name)
kubectl -n spring-bedrock-demo logs -f "$job" --pod-running-timeout=120s
kubectl -n spring-bedrock-demo wait --for=condition=complete "$job" --timeout=480s
```

Each run creates a new Job: 30 sequential requests, two seconds apart, with at most 16 paid Bedrock calls. It mixes valid prompts, rejected blank prompts and health checks, stops on an unexpected status or connection error, and never retries. Logs include the UTC capture window and `X-Demo-Run` marker. Jobs expire after one hour. Keep capture and snapshot configuration private.

## API contract and CI

The checked-in contract is [openapi.yaml](src/main/resources/static/openapi.yaml), served at [http://localhost:8080/openapi.yaml](http://localhost:8080/openapi.yaml). It documents requests, response fields, validation errors, dependency failures, and application health. Review contract changes with application changes; use a pinned revision when measuring schema coverage.

`./mvnw verify` runs the HTTP integration tests with a test-only replacement for the model. No AWS credentials or cloud calls are needed in CI. The runtime always uses Bedrock. GitHub Actions also validates the OpenAPI document, renders the Kubernetes overlay, and builds the container. Deployment is manual.

## Kubernetes

The reusable [Kubernetes base](k8s/base) provides one replica, a ClusterIP service, resource limits, a non-root container, and health probes. Supply your image and a `bedrock-credentials` Secret from a private deployment overlay. The application supports standard AWS environment credentials; cluster-specific credentials, capture configuration, storage settings, and endpoints belong outside this public repository.

Health checks do not call Bedrock. The API has no authentication or public ingress. Use the API client Job for demo traffic; port-forwarding is available for local debugging. The shared Speedscale skills and MCP settings belong in Kiro user configuration. This repository contains the application-specific spec, test runner and redacted traffic assets.

## License

[MIT-0](LICENSE), retaining the upstream AWS license.
