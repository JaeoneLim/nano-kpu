from pathlib import Path
import argparse
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from scripts import trace_quick


ROOT = Path(__file__).resolve().parents[1]
TRACE_TB = ROOT / "harness" / "tb" / "tb_trace.cpp"
TRACE_RUNNER = ROOT / "scripts" / "trace_quick.py"
FROZEN_TB = ROOT / "harness" / "tb" / "tb_main.cpp"


class TraceQuickTests(unittest.TestCase):
    def test_trace_is_isolated_from_frozen_evaluation_testbench(self):
        self.assertTrue(TRACE_TB.is_file(), "missing debug-only trace testbench")
        self.assertNotIn("verilated_fst_c", FROZEN_TB.read_text(encoding="utf-8").lower())

    def test_trace_testbench_writes_and_closes_fst(self):
        source = TRACE_TB.read_text(encoding="utf-8")
        for expected in (
            "#include <verilated_fst_c.h>",
            "Verilated::traceEverOn(true)",
            "top->trace(",
            "trace->dump(",
            "trace->close()",
            '"--trace-file"',
        ):
            self.assertIn(expected, source)

    def test_runner_builds_fst_trace_and_has_dry_run_cli(self):
        self.assertTrue(TRACE_RUNNER.is_file(), "missing trace runner")
        source = TRACE_RUNNER.read_text(encoding="utf-8")
        for expected in (
            "--trace-fst",
            "--trace-depth",
            "tb_trace.cpp",
            "nano-quick.fst",
            '"-CFLAGS"',
            '"-LDFLAGS"',
        ):
            self.assertIn(expected, source)
        result = subprocess.run(
            [sys.executable, str(TRACE_RUNNER), "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("--no-open", result.stdout)

    def test_trace_depth_is_forwarded_to_runtime_driver(self):
        runner = TRACE_RUNNER.read_text(encoding="utf-8")
        driver = TRACE_TB.read_text(encoding="utf-8")
        self.assertIn("def run_trace(image: Path, depth: int)", runner)
        self.assertIn('f"--trace-depth={depth}"', runner)
        self.assertIn("parse_trace_depth_arg(argc, argv, &trace_depth)", driver)
        self.assertIn("top->trace(trace, static_cast<int>(trace_depth))", driver)
        self.assertNotIn("top->trace(trace, 5)", driver)

    def test_trace_depth_validation_rejects_invalid_values_early(self):
        for value in ("0", "-1", "7junk", "2147483648"):
            with self.subTest(value=value):
                with self.assertRaises(argparse.ArgumentTypeError):
                    trace_quick.parse_trace_depth(value)
        self.assertEqual(trace_quick.parse_trace_depth("7"), 7)

    def test_cpp_trace_depth_parser_rejects_non_decimal_syntax(self):
        source = TRACE_TB.read_text(encoding="utf-8")
        helpers_start = source.index("static std::string arg_str(")
        helpers_end = source.index("\nint main(", helpers_start)
        parser_helpers = source[helpers_start:helpers_end]

        harness = """\
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
""" + parser_helpers + """
int main(int argc, char** argv) {
    uint64_t depth = 0;
    return parse_trace_depth_arg(argc, argv, &depth) ? 0 : 2;
}
"""
        compiler = shutil.which("c++")
        if compiler is None:
            self.fail("C++ compiler is required for parser regression")
        with tempfile.TemporaryDirectory() as temp:
            source_path = Path(temp) / "trace_depth_parser.cpp"
            binary = Path(temp) / "trace_depth_parser"
            source_path.write_text(harness, encoding="utf-8")
            subprocess.run(
                [compiler, "-std=c++14", str(source_path), "-o", str(binary)],
                check=True,
            )
            for value in (
                "-18446744073709551615",
                "-1",
                "+7",
                " 7",
                "7junk",
                "0",
                "2147483648",
            ):
                with self.subTest(value=value):
                    result = subprocess.run([str(binary), f"--trace-depth={value}"])
                    self.assertEqual(result.returncode, 2)
            for value in ("1", "7", "2147483647"):
                with self.subTest(value=value):
                    result = subprocess.run([str(binary), f"--trace-depth={value}"])
                    self.assertEqual(result.returncode, 0)

    def test_trace_model_cache_is_keyed_by_depth(self):
        with tempfile.TemporaryDirectory() as temp:
            objdir = Path(temp) / "obj"
            binary = objdir / "tb_trace"
            calls = []

            def fake_build(command, **_kwargs):
                calls.append(command)
                objdir.mkdir(parents=True, exist_ok=True)
                binary.write_text("fake trace binary", encoding="utf-8")

            with (
                mock.patch.object(trace_quick, "OBJDIR", objdir),
                mock.patch.object(trace_quick, "TRACE_BIN", binary),
                mock.patch.object(trace_quick, "rtl_sources", return_value=[]),
                mock.patch.object(trace_quick.shutil, "which", return_value=None),
                mock.patch.object(trace_quick.subprocess, "run", side_effect=fake_build),
            ):
                trace_quick.build_trace_model(5, True)
                trace_quick.build_trace_model(5, False)
                trace_quick.build_trace_model(7, False)

            self.assertEqual(len(calls), 2)
            self.assertEqual((objdir / ".trace-depth").read_text(encoding="utf-8"), "7\n")


if __name__ == "__main__":
    unittest.main()
