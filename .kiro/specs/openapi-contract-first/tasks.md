# Tasks: OpenAPI Contract-First Development

Status: proposed; no implementation tasks are complete. Each item is a small verifiable step toward the requirements in this folder.

- [ ] 1. Establish the failing cases.
  - Extend the HTTP tests for Unicode length/blankness, missing bodies, wrong method/media type, and health failure.
  - Record actual outcomes and identify contract mismatches without calling AWS.
  - Requirements: 3, 4.

- [ ] 2. Add reliable test-scoped schema validation.
  - Select and pin a validator that reads the OpenAPI document and passes the validator checks in the design.
  - Add separate helpers for valid requests and intentionally invalid requests; validate actual responses in both.
  - Replace the existing field-name helper after demonstrating that meaningful schema violations fail.
  - Requirements: 2.

- [ ] 3. Align request validation with the published contract.
  - Count prompt length in Unicode code points and match the published whitespace rule.
  - Prove agreement at ASCII and emoji boundaries and for the whitespace cases.
  - Preserve the error response and verify rejected requests never call the model.
  - Requirements: 3.

- [ ] 4. Complete endpoint coverage.
  - Add health/probe, 405/415, and served-contract documentation based on observed behavior.
  - Validate all supported chat outcomes, health/probe success and failure, and the served YAML resource.
  - Keep route-removal tests separate and restore any test health state.
  - Requirements: 4.

- [ ] 5. Verify and hand off.
  - Run Maven verification and the existing OpenAPI validity check; confirm conformance runs through the existing CI job.
  - Update the baseline to describe the resulting behavior.
  - Open a PR with a compact coverage table, results, and any remaining gaps.
  - Requirements: 1, 5.
