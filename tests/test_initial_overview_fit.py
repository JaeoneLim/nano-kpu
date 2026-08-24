from pathlib import Path
import re
import unittest


HTML = Path(__file__).resolve().parents[1] / "docs" / "nano-kpu-rtl-architecture.html"


class InitialOverviewFitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = HTML.read_text(encoding="utf-8")

    def test_overview_stage_is_hidden_until_first_fit(self):
        """The native 6120×5380 image must never flash at 1:1 on first paint."""
        self.assertRegex(
            self.page,
            r"#stage:not\(\.fitReady\)\{visibility:hidden\}",
        )
        self.assertIn("stage.classList.add('fitReady')", self.page)

    def test_cached_image_still_runs_initial_fit(self):
        """Fit must run when the image completed before onload was assigned."""
        self.assertRegex(
            self.page,
            r"img\.onload=fit;if\(img\.complete&&img\.naturalWidth\)fit\(\)",
        )


if __name__ == "__main__":
    unittest.main()
