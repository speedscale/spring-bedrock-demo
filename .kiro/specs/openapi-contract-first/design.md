# Design: OpenAPI Contract-First Development

## Scope

Keep the existing controller/service structure, hand-written contract, `TestRestTemplate` HTTP tests, and GitHub Actions workflow. Add conformance validation to the test suite. Runtime dependencies, deployment, capture, and credentials are outside this change.

## Development loop

1. Describe the requested behavior and edit `openapi.yaml`.
2. Add or adjust an HTTP test that exposes the missing behavior.
3. Implement the change.
4. Run Maven verification and OpenAPI validation.
5. Review the contract and app change in one PR, updating the baseline where needed.

These steps describe work order, not a requirement for a separate approval or commit at every step. This document guides work when consulted; it does not install an always-on Kiro steering rule.

## Test helper

Choose a pinned test-scoped OpenAPI validator after checking its behavior against this contract. Before replacing `assertContractResponse`, demonstrate that the new validation detects a missing required field, wrong type, extra property, oversized string, blank prompt, and undocumented status/media type. Resolve local `$ref` values from the document.

Provide explicit valid-request and invalid-request paths. The first requires a valid request and response. The second asserts the intended request failure, sends the invalid input to the app, validates the actual 400 response, and verifies no model interaction. Keep independent parse assertions for malformed JSON and separate route-removal tests.

Validate the raw received response, including its actual status and media type. Use schema-specific fixtures to test the validator; do not inject test-only validation behavior into the application.

## Unicode agreement

The current Java length annotation and the contract do not use the same counting unit. Keep the contract's code-point limit and update application validation to match. Preserve the existing error JSON.

Use a small explicit constraint where built-in annotations cannot express the contract. Cover mixed text and supplementary characters at the boundary. Determine blankness from the published pattern's whitespace semantics and verify the same cases in both validators. A permissive validator must not silently redefine the public contract.

## Endpoint coverage

| Surface | Planned evidence |
|---|---|
| Chat 200 | Valid prompt/response, message composition, ASCII and Unicode boundaries |
| Chat 400 | Invalid bodies, expected request-validation failures, schema-valid error, no model call |
| Chat 503 | Model exception and missing/blank output with a schema-valid sanitized error |
| Health and probes | Healthy and unhealthy responses with isolated test fixtures, no model call |
| Unsupported method/media type | Measured 405/415 behavior, documented actual media types and body shapes |
| Served contract | Resource equality and YAML media type matching the app's actual response |

Use a short coverage table in the PR rather than building a coverage framework. Preserve Spring error behavior and health semantics while documenting them accurately.

## CI and completion

Use `./mvnw -B -ntp verify` and the existing `openapi-spec-validator==0.7.2` check. New conformance tests run as part of Maven verification. No Spectral, oasdiff, compatibility opt-in labels, generated server interfaces, or additional CI service is needed for this plan.

Completion means the documented cases have passing tests, the contract is valid, and the PR states remaining limitations. It does not mean the app was deployed or a live Bedrock call was made.
