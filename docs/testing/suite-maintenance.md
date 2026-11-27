# Add local traffic to an existing suite

## Cover the new ticket-summary operation

`POST /api/chat/summary` returns a concise summary of a support ticket for an agent. The accepted recording covers `POST /api/chat` and `GET /actuator/health`. Replay the accepted suite against the app with ticket summaries enabled and use the checked-in OpenAPI spec for the baseline. The summary operation should appear as a coverage gap.

Record a valid sample ticket and a blank ticket through the inbound recording proxy. Use the [capture command below](#review-the-local-capture), a fresh output directory, and an authorized dev account. Wait for the local app to be ready before sending requests.

```bash
curl -fsS http://127.0.0.1:14193/api/chat/summary \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"The reset link worked, but the app rejects the new password."}'
curl -sS -w '\nHTTP %{http_code}\n' http://127.0.0.1:14193/api/chat/summary \
  -H 'Content-Type: application/json' -d '{"prompt":""}'
```

The valid ticket returns HTTP 200 and makes one Bedrock call. The blank ticket returns HTTP 400 before making a dependency call. Stop the recorder, review the recorded responses and redaction, and retain the matching outbound Bedrock pair beside the two inbound cases. Use sample ticket text without personal data.

Use this prompt in Kiro Crew. Supply the fresh recording path when asked.

> Add the new ticket-summary recording to the existing suite. Keep every original test and mock. Replay the combined suite and show what changed in OpenAPI coverage.

Build a separate candidate with [the existing copy helper](#assemble-a-candidate). If you replay that candidate with the old mocks, the summary request should fail because the mock has no matching response. Supply the captured Bedrock pair and rerun the full suite. Compare the passing baseline and candidate using the same OpenAPI file and app revision. Show the newly exercised operation and the remaining error-path gaps. Leave the candidate for review.

## Earlier rehearsal on the chat operation

The accepted `support-chat` suite has 10 inbound cases and two Bedrock responses used during replay. This example adds a new question to the existing `POST /api/chat` endpoint and checks the 4,000-character input limit. Application code and the OpenAPI contract stay at the same revision.

The additions are synthetic demo traffic recorded locally against a dev Bedrock account on November 18, 2026. The successful response is the response captured from that call. It is frozen for repeatable integration testing; it does not establish model quality or whether a future live model will give the same answer. Authorization and session-token headers were redacted at capture time. No IHG traffic is included.

[Native rehearsal results](maintenance-report.md) show the expected failure and two passing expanded runs.

## Review the local capture

The new pairs are in `proxymock/recordings/support-chat-local-additions/`. Review the inbound success response, its outbound Bedrock request and response, and the validation rejection. The new support question is `How can I change the email address on my account?`. The boundary request has 4,001 `x` characters and returns HTTP 400.

To collect a different scenario, launch the app directly under `proxymock record` from this repository, using a fresh output directory and a reviewed DLP policy. With Java 21, your authorized dev credentials in the environment, and the app built:

```bash
proxymock --config "$DEMO_CONFIG" --context my-context record \
  --out proxymock/recordings/my-local-additions \
  --dlp-config proxymock/dlprules/spring-bedrock-demo-capture.json \
  --svc-name spring-bedrock-demo \
  --app-port 18191 --proxy-in-port 14193 --proxy-out-port 14190 \
  -- "$JAVA_HOME/bin/java" -jar target/app.jar
```

Send requests through port 14193 so both inbound traffic and outbound dependencies are captured. Stop the recorder after the scenario. A live success makes a paid Bedrock call. Review headers, decoded bodies and metadata before sharing or adding fixtures to Git. Keep real credentials and private configuration outside the repository. Use the appropriate explicit CLI config/context for your environment.

## Assemble a candidate

Use a new output directory. The helper copies Markdown RRPairs, rejects duplicate filenames or UUIDs and refuses to overwrite an existing candidate. It records source labels, UUIDs and SHA-256 hashes in `provenance.json`; both input recordings remain unchanged. Binary-protocol fixtures require a separate workflow.

```bash
python3 scripts/extend-recording.py \
  proxymock/recordings/support-chat \
  proxymock/recordings/support-chat-local-additions \
  proxymock/tmp/support-chat-maintained
export PROXYMOCK_IT_RECORDING=proxymock/tmp/support-chat-maintained
export PROXYMOCK_IT_APP_PORT=18191
export PROXYMOCK_IT_PROXY_PORT=14191
```

Check that each original RRPair has the same bytes in the candidate. Keep generated candidates and results out of Git; commit the reviewed additions and reusable instructions.

## Demonstrate the missing dependency

Run the expanded inbound suite against the original mocks:

```bash
PROXYMOCK_IT_MOCK_RECORDING=proxymock/recordings/support-chat \
  scripts/proxymock-it.sh maintenance-old-mocks
```

The new successful question has no matching Bedrock response in the old recording. With passthrough disabled, it returns HTTP 503 instead of the recorded 200 and fails two assertions. Inspect the native replay verdict, assertion failures and mock MISS evidence. Leave the expected response unchanged. That failed run reports higher status coverage because it exercised an error response; the failed expectation still disqualifies the candidate.

Then use the expanded mocks and repeat the complete suite:

```bash
scripts/proxymock-it.sh maintenance-a
scripts/proxymock-it.sh maintenance-b
python3 scripts/proxymock-it-report.py report \
  proxymock/results/maintenance-a proxymock/results/maintenance-b
```

The candidate contains the original 10 inbound cases plus the two new cases. All 12 must pass with three Bedrock HITs, zero MISSes and zero passthrough calls. Local replay uses dummy credentials and captured dependency responses. A passing candidate still needs human review before it becomes the accepted suite.

## Maintain the suite as behavior changes

Capture each new scenario into its own directory. Review request coverage and the behavior being asserted before copying it into a candidate. A new input on an existing operation can improve scenario coverage without changing OpenAPI coverage percentages. This addition keeps coverage at 2/2 operations, 3/5 documented statuses and 4/7 fields; HTTP 503 remains a gap.

When an intentional API or dependency change alters an existing expectation, review that expectation as a separate change with its reason and captured evidence. Keep the prior recording available for comparison. Do not replace expected responses with observed failures to obtain a passing run. Run the complete candidate twice at a fixed application and contract revision, then review the diff and validation evidence together.

## Run the workflow in Kiro Crew

Open this repository as the Crew workspace. Give it the prompt in [crew-maintenance-prompt.md](crew-maintenance-prompt.md). The recording and runner are prepared inputs; the agent assembles and validates the candidate. Inspect the actual terminal results and approve the candidate diff before promoting it. An edited video should disclose prepared fixtures and any omitted waiting.
