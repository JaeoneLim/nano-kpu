#!/usr/bin/env python3
"""Build a debug-only Verilator FST model, run the latest quick image, and open Surfer."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
OBJDIR = BUILD / "verilator_trace"
WAVEDIR = BUILD / "waves"
TRACE_TB = ROOT / "harness" / "tb" / "tb_trace.cpp"
TRACE_BIN = OBJDIR / "tb_trace"
TRACE_FILE = WAVEDIR / "nano-quick.fst"


def run(command: list[str]) -> None:
    print("$", shlex.join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def rtl_sources() -> list[str]:
    sources: list[str] = []
    for line in (ROOT / "rtl" / "filelist.f").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "//")):
            sources.append(line)
    sources.extend([
        str(ROOT / "harness" / "macros" / "msh_sram.v"),
        str(ROOT / "harness" / "macros" / "msh_rom.v"),
    ])
    return sources


def ensure_quick_input() -> Path:
    images = sorted(BUILD.glob("img_nano_*_1_*.bin"), key=lambda p: p.stat().st_mtime)
    if not images:
        run(["make", "quick"])
        images = sorted(BUILD.glob("img_nano_*_1_*.bin"), key=lambda p: p.stat().st_mtime)
    if not images:
        raise SystemExit("quick input image was not generated")
    image = images[-1]
    if not Path(f"{image}.layout.json").is_file():
        raise SystemExit(f"missing layout metadata: {image}.layout.json")
    return image


def build_trace_model(depth: int, rebuild: bool) -> None:
    source_paths = [TRACE_TB] + [ROOT / s for s in rtl_sources() if not Path(s).is_absolute()]
    source_paths += [Path(s) for s in rtl_sources() if Path(s).is_absolute()]
    stale = not TRACE_BIN.is_file() or any(
        p.is_file() and p.stat().st_mtime > TRACE_BIN.stat().st_mtime for p in source_paths
    )
    if not (rebuild or stale):
        print(f"[trace] reusing {TRACE_BIN}")
        return
    shutil.rmtree(OBJDIR, ignore_errors=True)
    brew_prefix = None
    if sys.platform == "darwin" and shutil.which("brew"):
        brew_prefix = subprocess.check_output(
            ["brew", "--prefix"], text=True
        ).strip()
    brew_flags = ([
        "-CFLAGS", f"-I{brew_prefix}/include",
        "-LDFLAGS", f"-L{brew_prefix}/lib",
    ] if brew_prefix else [])
    command = [
        "verilator", "--cc", "--exe", "--build", "-j", "8", "-O2",
        "-Wno-fatal", "--top-module", "msh_chip_top", "--x-initial", "unique",
        "--trace-fst", "--trace-structs", "--trace-depth", str(depth),
        *brew_flags,
        "--Mdir", str(OBJDIR), "-o", "tb_trace", str(TRACE_TB),
        *rtl_sources(),
    ]
    env = os.environ.copy()
    if sys.platform == "darwin" and "-std=" not in env.get("CXXFLAGS", ""):
        env["CXXFLAGS"] = f"-std=c++14 {env.get('CXXFLAGS', '')}".strip()
    print("$", shlex.join(command), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def previous_timing_args() -> dict[str, str]:
    defaults = {
        "lat-base": "24",
        "lat-jitter": "24",
        "stall-permille": "50",
        "timing-seed": "2299918149706686108",
    }
    log = BUILD / "sim_rtl_nano_1.log"
    if not log.is_file():
        return defaults
    first = log.read_text(encoding="utf-8").splitlines()[0]
    for token in shlex.split(first.removeprefix("$ ")):
        if token.startswith("--") and "=" in token:
            key, value = token[2:].split("=", 1)
            if key in defaults:
                defaults[key] = value
    return defaults


def run_trace(image: Path) -> None:
    WAVEDIR.mkdir(parents=True, exist_ok=True)
    TRACE_FILE.unlink(missing_ok=True)
    layout = json.loads(Path(f"{image}.layout.json").read_text(encoding="utf-8"))
    out_base = int(layout["out_logits_addr"])
    out_len = int(layout["out_status_addr"]) + 16 - out_base
    timing = previous_timing_args()
    result = WAVEDIR / "nano-quick-result.bin"
    command = [
        str(TRACE_BIN),
        f"--image={image}",
        f"--result={result}",
        f"--out-base={out_base}",
        f"--out-len={out_len}",
        "--timeout=300000000",
        *(f"--{key}={value}" for key, value in timing.items()),
        f"--trace-file={TRACE_FILE}",
    ]
    run(command)
    if not TRACE_FILE.is_file() or TRACE_FILE.stat().st_size == 0:
        raise SystemExit("trace run completed without a non-empty FST file")
    print(f"[trace] wrote {TRACE_FILE} ({TRACE_FILE.stat().st_size / 1024 / 1024:.1f} MiB)")


def open_surfer() -> None:
    surfer = shutil.which("surfer")
    if not surfer:
        raise SystemExit("Surfer is not installed; run: brew install surfer")
    subprocess.Popen(
        [surfer, str(TRACE_FILE)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    print(f"[trace] opened {TRACE_FILE} in Surfer")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-depth", type=int, default=5,
                        help="Verilator hierarchy depth to trace (default: 5)")
    parser.add_argument("--rebuild", action="store_true",
                        help="force rebuilding the traced Verilator model")
    parser.add_argument("--no-open", action="store_true",
                        help="generate the FST without launching Surfer")
    args = parser.parse_args()
    image = ensure_quick_input()
    build_trace_model(args.trace_depth, args.rebuild)
    run_trace(image)
    if not args.no_open:
        open_surfer()


if __name__ == "__main__":
    main()
