from pathlib import Path
import subprocess
import sys
import unittest


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


if __name__ == "__main__":
    unittest.main()
