# Approved recorded-traffic testing spec

The review split the draft into [requirements](requirements.md), [design](design.md), and [tasks](tasks.md). Read all three files before implementing. They replace the earlier draft in chat.

Use the already-reviewed `proxymock/recordings/support-chat/` fixture and existing capture policy. No new capture, fixture migration, DLP application, fault injection or synthetic failure experiment is required. Start the app with the absolute Java 21 binary directly under the proxymock wrapper. Keep reusable traffic assets in Git. Run twice unchanged and report native comparison, evaluated assertions, mock outcomes and OpenAPI coverage.
