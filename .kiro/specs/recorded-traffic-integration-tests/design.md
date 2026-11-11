# Test flow

The Kubernetes API client sends requests to the deployed Service. Speedscale captures inbound API calls and outbound Bedrock and STS calls. The forwarder's active DLP policy redacts the exported traffic before it reaches the configured storage destinations. Fresh capture verification is an off-camera prerequisite.

For local testing, one frozen, verified redacted recording provides inbound tests and outbound dependency mocks. Proxymock wraps the Java 21 process to configure JVM proxying and trust. Native replay drives the local app; its local target address is expected here. Production capture continues to come from the Kubernetes Service rather than a laptop loopback port.

Use the existing OpenAPI file as the denominator for native recorded and replayed coverage. Keep baseline and replay inputs distinct. Outbound dependency pairs supply mocks and do not become inbound API coverage cases. Record the selected fixture identity, app revision, contract digest, proxymock version and active test configuration once.

One runner at `scripts/proxymock-it.sh` accepts a run name and uses the accepted recording. It starts the mock-wrapped app, waits for readiness, replays once with native regression assertions and the OpenAPI contract, saves native verdict/mock/coverage outputs, then stops its own processes. Invoke the same runner for two separate run names without changing its inputs. Build only when needed. Shell orchestration and a small summary parser are sufficient; preserve nonzero exit status through report generation.

Use `proxymock/recordings/` for reviewed redacted fixtures and the native workspace locations for test configuration and DLP rules. Ignore specific generated run/log paths. Raw cloud or bucket pulls remain in a private staging location until reviewed. Do not treat a DLP label, a filename or a gitignore rule as evidence of sanitization.

The report starts with both run verdicts, followed by response matches, evaluated assertions, Bedrock HIT/MISS/PASSTHROUGH and native coverage fractions. List coverage gaps and unused mocks. Link the underlying native outputs. Do not invent an HTML dashboard; a short Markdown report is sufficient for this video.

Any required test-config tuning happens before the acceptance pair. Freeze its content and reuse it unchanged. Redaction may require consistent replacements across related pairs; prove the redacted fixture still produces correct comparisons and HITs before calling it ready.
