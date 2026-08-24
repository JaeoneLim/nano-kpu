#!/usr/bin/env python3
"""Build the curated static GitHub Pages artifact for nano-kpu docs."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

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
    """Allow only the workflow site directory or a safe child of the temp root."""
    candidate = output.expanduser()
    if candidate.is_symlink():
        raise ValueError(f"refusing symlink Pages output path: {candidate}")
    resolved = candidate.resolve()
    workflow_site = (ROOT / "_site").resolve()
    if resolved == workflow_site:
        return resolved

    if resolved == ROOT or resolved in ROOT.parents:
        raise ValueError(f"refusing repository root or ancestor: {resolved}")
    for source in (DOCS, ROOT / "rtl", ROOT / "scripts", ROOT / "tests", ROOT / ".git"):
        if resolved == source or source in resolved.parents:
            raise ValueError(f"refusing output inside repository sources: {resolved}")

    temp_root = Path(tempfile.gettempdir()).resolve()
    if temp_root in resolved.parents:
        return resolved
    raise ValueError(f"refusing unsafe Pages output path: {resolved}")


def build(output: Path) -> None:
    output = validate_output_path(output)

    if output.exists():
        shutil.rmtree(output)
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
