# Third-Party Notices

Unless otherwise noted, this modified fork of
[MoonshotAI/nano-kpu](https://github.com/MoonshotAI/nano-kpu) is distributed
under the Apache License 2.0 in the repository root.

## Highlight.js

The files under `docs/vendor/` contain Highlight.js 11.11.1 components,
distributed under the BSD 3-Clause License. The complete license is provided
at `docs/vendor/LICENSE.highlightjs-BSD-3-Clause`.

## Surfer

Waveform screenshots under `docs/assets/waveforms/` were rendered with
[Surfer](https://gitlab.com/surfer-project/surfer), which is distributed under
the European Union Public Licence 1.2 (EUPL-1.2). The screenshots document
traces generated from this nano-kpu fork. Surfer's application, source,
WebAssembly bundle, and web distribution are not included in this repository
or its GitHub Pages artifact.

## Nangate45 standard-cell library

`harness/lib/NangateOpenCellLibrary_typical.lib` is not distributed with this
repository or its GitHub Pages artifact. `scripts/setup_env.sh` downloads the
library separately from a pinned OpenROAD-flow-scripts revision and verifies
its SHA-256 digest. See `third_party/licenses/nangate45.LICENSE` and the notices
embedded in the downloaded library for applicable terms.