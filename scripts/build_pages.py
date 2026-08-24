#!/usr/bin/env python3
"""Build the curated static GitHub Pages artifact for nano-kpu docs."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PAGES_OUTPUT = ROOT / "_site"

FILES = (
    "nano-kpu-rtl-architecture.html",
    "rtl-source-viewer.html",
    "nano-kpu-rtl-architecture.png",
    "nano-kpu-full-rtl.png",
    "nano-kpu-rtl-architecture.excalidraw",
    "nano-kpu-full-rtl.excalidraw",
    "rtl-structure-notes.md",
)
DIRECTORIES = ("assets", "token-journey", "vendor")
RTL_FILES = (
    "msh_chip_top.v",
    "msh_seq.v",
    "msh_fetch.v",
    "msh_deq.v",
    "msh_gemv.v",
    "msh_vec.v",
    "msh_kda.v",
    "msh_mla.v",
    "msh_mem.v",
    "msh_lg.v",
)
FORBIDDEN_SUFFIXES = {".fst", ".lib", ".sucl"}

def validate_output_path(output: Path) -> Path:
    """Authorize only the repository's fixed Pages workflow destination."""
    candidate = Path(os.path.abspath(output.expanduser()))
    approved = Path(os.path.abspath(PAGES_OUTPUT))
    if candidate != approved:
        raise ValueError(f"refusing non-workflow Pages output: {candidate}")
    if candidate.is_symlink():
        raise ValueError(f"refusing symlink Pages output path: {candidate}")
    return candidate.resolve()


def build(output: Path) -> None:
    output = validate_output_path(output)

    if output.exists():
        raise FileExistsError(f"refusing to replace existing Pages output: {output}")
    output.mkdir(parents=True)

    for relative in FILES:
        source = DOCS / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, output / relative)

    for relative in DIRECTORIES:
        source = DOCS / relative
        if not source.is_dir():
            raise FileNotFoundError(source)
        shutil.copytree(source, output / relative)

    rtl_output = output / "rtl"
    rtl_output.mkdir()
    for relative in RTL_FILES:
        source = ROOT / "rtl" / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, rtl_output / relative)

    shutil.copy2(DOCS / "nano-kpu-rtl-architecture.html", output / "index.html")
    shutil.copy2(ROOT / "LICENSE", output / "LICENSE")
    shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", output / "THIRD_PARTY_NOTICES.md")
    (output / ".nojekyll").touch()

    published = [path for path in output.rglob("*") if path.is_file()]
    forbidden = [
        path
        for path in published
        if path.suffix.lower() in FORBIDDEN_SUFFIXES
        or "surfer-web" in path.parts
        or ".venv" in path.parts
        or "build" in path.parts
    ]
    if forbidden:
        names = ", ".join(str(path.relative_to(output)) for path in forbidden)
        raise RuntimeError(f"forbidden Pages content: {names}")

    print(f"Built {len(published)} curated Pages files in {output}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_pages.py OUTPUT_DIRECTORY")
    build(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
