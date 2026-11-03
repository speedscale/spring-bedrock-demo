# Requirements: OpenAPI Contract-First Development

## Purpose and status

This is a small, proposed improvement to the existing contract checks. It is not implemented. The goal is simple: an API change updates the OpenAPI document, the HTTP tests, and the app together.

The current CI validates OpenAPI structure, while selected tests check response field names. Full schema validation is still missing. This plan adds test-scoped conformance checks using the existing Maven/CI workflow. It does not add a linter, a compatibility service, PR labels, code generation, or a version-governance project.

## 1. Keep the contract and behavior together

1. For an API change, edit `src/main/resources/static/openapi.yaml` before implementation and include the contract, tests, and implementation in the same PR. Internal changes need no contract edit.
2. The contract remains a single hand-written OpenAPI 3.0.3 file served at `/openapi.yaml`.
3. Update the baseline spec when behavior changes. Routine implementation choices proceed within the requested scope; ask only when the requested behavior is ambiguous or a consequential scope change is needed.

## 2. Validate successful and rejected requests correctly

1. Tests for valid requests must pass request validation against the contract and validate the actual response status, media type, and body.
2. Tests with deliberately invalid input must assert the expected request-validation failure and the app's 400 response. They must not require the invalid request to pass schema validation.
3. For malformed JSON or an absent body, use a parse/body-validation failure assertion. In every rejection case, assert that the model was not called and validate the returned error body.
4. A schema validator must read the checked-in contract and enforce its constraints, including references, required fields, types, lengths, patterns, and `additionalProperties`. Its dependency is test-scoped and pinned.
5. Tests must reject undocumented responses for operations being checked. Removed-route 404 tests remain separate from conformance tests for documented operations.
6. All automated tests run with a mocked model and no AWS calls.

## 3. Make request constraints agree

1. Probe empty input, 1/4000/4001 ASCII characters, supplementary Unicode characters, ASCII and non-ASCII whitespace, non-string values, unknown fields, null, and absent bodies.
2. Preserve the existing published contract as the target: `maxLength: 4000` counts Unicode code points, and `pattern: '\S'` requires a character outside the pattern's whitespace set. Align application validation and the chosen validator with those semantics.
3. Include cases at 4000 and 4001 emoji, plus U+00A0, U+2003, tabs, and newlines. Confirm behavior with tests using the installed validation library; do not assume `@NotBlank` uses `trim()`.
4. A prose description is not a fix for a machine-readable constraint mismatch. Tests must establish agreement. Report any remaining incompatibility explicitly.

## 4. Cover the supported API surface

1. Validate chat success (200), rejected input (400), and dependency failure (503), including blank model output.
2. Document and test the main health endpoint and both probe paths. Exercise healthy and unhealthy responses with test-only state or health contributors; preserve real production behavior and restore test state.
3. Characterize 405 and 415 responses before documenting them. Preserve Spring's default response shape unless a requested feature needs a new error contract.
4. Document `GET /openapi.yaml` as a YAML resource, without inventing a recursive schema for its document body. Test that the served content matches the checked-in resource.
5. Do not delete a real supported response merely because it needs a test fixture.

## 5. Finish with reviewable evidence

1. Run Maven verification and the existing OpenAPI validity check. Keep these checks in the existing CI workflow.
2. Report the contract change, passing checks, and any remaining gaps in the PR. Do not claim live AWS verification from mocked tests.
3. Mark a task complete only when its acceptance criteria have been exercised.
