# Local suite additions

Synthetic support-chat traffic captured locally on November 18, 2026, with Java 21 and proxymock v2.5.1413 against a dev Bedrock account. No customer traffic is included. Authorization and session-token headers were redacted during capture using the checked-in DLP policy. The bodies remain the observed request and response payloads.

| File | Direction | Scenario | Status |
| --- | --- | --- | --- |
| `localhost/2026-11-18_17-15-33.657239Z.md` | IN | Change the email address on an account | 200 |
| `bedrock-runtime.us-east-1.amazonaws.com/2026-11-18_17-15-33.953695Z.md` | OUT | Bedrock response for the new question | 200 |
| `localhost/2026-11-18_17-15-36.172904Z.md` | IN | Prompt length 4,001 exceeds the 4,000-character limit | 400 |

[Assemble and validate a candidate](../../../docs/testing/suite-maintenance.md). These additions remain separate from the accepted `support-chat` baseline. A generated candidate needs human review before promotion. Replays use the frozen Bedrock response and dummy AWS credentials; they make no live model calls.
