# Architecture diagrams

The README embeds SVG exports so AWS icons render on GitHub. The editable Mermaid sources are [application.mmd](application.mmd), [capture-storage.mmd](capture-storage.mmd), and [local-testing.mmd](local-testing.mmd). Namespace names are examples, including `observability` for the collector; actual cluster settings stay in a private overlay.

To regenerate, install Node.js and Chrome/Chromium, then run `npm ci` and `npm run render` in this directory. Set `CHROME_BIN` if Chrome is not at the macOS default path. Commit the updated Mermaid sources and SVGs together. The renderer also creates local HTML viewers and 4K PNGs, which are ignored by Git.

The renderer uses [Mermaid icon registration](https://mermaid.js.org/config/icons.html) to load `aws-icons.json`. A Markdown renderer needs that icon pack to display these Mermaid sources directly. The SVG exports contain the icons and do not fetch external assets.

The local testing diagram describes the demo workflow. The starting app has no proxymock installation, captured traffic or replay configuration. The collector archives traffic; named bucket snapshots are created separately through the CLI.

AWS architecture icons are Amazon Web Services assets, used under the permissions on the [AWS architecture icons page](https://aws.amazon.com/architecture/icons/). The diagrams use the July 2026 icon release.
