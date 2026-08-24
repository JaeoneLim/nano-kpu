import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


class PublicationReadinessTests(unittest.TestCase):
    def test_pages_builder_refuses_dangerous_output_paths(self):
        from scripts.build_pages import validate_output_path

        for dangerous in (
            Path("/"),
            Path(tempfile.gettempdir()),
            ROOT,
            ROOT.parent,
            ROOT / "docs",
            ROOT / "docs/generated-site",
            ROOT / "rtl",
            ROOT / "scripts",
            ROOT / "tests",
            ROOT / ".git",
        ):
            with self.subTest(path=dangerous):
                with self.assertRaises(ValueError):
                    validate_output_path(dangerous)

        with tempfile.TemporaryDirectory() as tmp:
            safe = Path(tmp) / "site"
            with self.assertRaises(ValueError):
                validate_output_path(safe)
            target = Path(tmp) / "target"
            target.mkdir()
            link = Path(tmp) / "site-link"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(ValueError):
                validate_output_path(link)

    def test_pages_builder_rejects_repository_children_under_temp(self):
        from scripts import build_pages

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            with mock.patch.object(build_pages, "PAGES_OUTPUT", repo / "_site"):
                self.assertEqual(
                    build_pages.validate_output_path(repo / "_site"),
                    (repo / "_site").resolve(),
                )
                victim = repo / "review-victim"
                victim.mkdir()
                marker = victim / "marker"
                marker.write_text("keep")
                with self.assertRaises(ValueError):
                    build_pages.build(victim)
                self.assertEqual(marker.read_text(), "keep")

    def test_pages_builder_rejects_symlinked_output_ancestors(self):
        from scripts.build_pages import build

        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            target = temp / "target"
            target.mkdir()
            alias = temp / "alias"
            alias.symlink_to(target, target_is_directory=True)
            site = target / "site"
            site.mkdir()
            marker = site / "marker"
            marker.write_text("keep")
            with self.assertRaises(ValueError):
                build(alias / "site")
            self.assertEqual(marker.read_text(), "keep")

    def test_pages_builder_never_replaces_an_existing_output(self):
        from scripts import build_pages

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "site"
            output.mkdir()
            marker = output / "marker"
            marker.write_text("keep")
            with mock.patch.object(build_pages, "PAGES_OUTPUT", output):
                with self.assertRaises(FileExistsError):
                    build_pages.build(output)
            self.assertEqual(marker.read_text(), "keep")

    def test_pages_builder_site_symlink_cannot_redefine_approved_output(self):
        from scripts import build_pages

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            victim = repo / "review-victim"
            (repo / "_site").symlink_to(victim, target_is_directory=True)
            with mock.patch.object(build_pages, "PAGES_OUTPUT", repo / "_site"):
                with self.assertRaises(ValueError):
                    build_pages.build(repo / "_site")
                with self.assertRaises(ValueError):
                    build_pages.build(victim)
            self.assertFalse(victim.exists())

    def test_license_and_fork_notices_are_present(self):
        gitignore = (ROOT / ".gitignore").read_text()
        readme = (ROOT / "README.md").read_text()
        trace_driver = (ROOT / "harness/tb/tb_trace.cpp").read_text()
        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text()
        highlight_license = (
            ROOT / "docs/vendor/LICENSE.highlightjs-BSD-3-Clause"
        ).read_text()

        self.assertIn(".venv/", gitignore)
        self.assertIn("## Changes in this fork", readme)
        self.assertIn("not endorsed by Moonshot AI", readme)
        self.assertIn("Derived from harness/tb/tb_main.cpp", trace_driver)
        self.assertIn("SPDX-License-Identifier: Apache-2.0", trace_driver)
        self.assertIn("Highlight.js", notices)
        self.assertIn("Surfer", notices)
        self.assertIn("BSD 3-Clause License", highlight_license)
        self.assertIn("Copyright (c) 2006, Ivan Sagalaev", highlight_license)

    def test_ci_and_pages_workflows_have_required_checks_and_permissions(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text()
        pages = (ROOT / ".github/workflows/pages.yml").read_text()

        self.assertIn("python3 -m unittest discover -s tests -v", ci)
        self.assertIn("make lint", ci)
        self.assertIn("pull_request:", ci)
        self.assertIn(
            "actions/checkout@11d5960a326750d5838078e36cf38b85af677262", ci
        )
        self.assertIn(
            "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", ci
        )

        self.assertIn("pages: write", pages)
        self.assertIn("id-token: write", pages)
        self.assertIn(
            "actions/configure-pages@983d7736d9b0ae728b81ab479565c72886d7745b",
            pages,
        )
        self.assertIn(
            "actions/upload-pages-artifact@56afc609e74202658d3ffba0e8f6dda462b719fa",
            pages,
        )
        self.assertIn(
            "actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e",
            pages,
        )
        self.assertIn("python3 scripts/build_pages.py", pages)
        self.assertIn('- "rtl/**"', pages)

    def test_rtl_source_viewer_is_pages_relative_and_escapes_query_errors(self):
        viewer = (ROOT / "docs/rtl-source-viewer.html").read_text()
        architecture = (ROOT / "docs/nano-kpu-rtl-architecture.html").read_text()

        self.assertIn("fetch(`rtl/${file}`", viewer)
        self.assertIn("fetch(`rtl/${info.file}`", architecture)
        self.assertNotIn("fetch(`../rtl/", viewer + architecture)
        self.assertIn("Invalid module name", viewer)
        self.assertNotIn("outerHTML", viewer)

    def test_pages_builder_publishes_only_curated_documentation(self):
        from scripts import build_pages

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "site"
            with mock.patch.object(build_pages, "PAGES_OUTPUT", out):
                build_pages.build(out)

            required = {
                "index.html",
                "nano-kpu-rtl-architecture.html",
                "rtl-source-viewer.html",
                "nano-kpu-rtl-architecture.png",
                "nano-kpu-full-rtl.png",
                "assets/waveforms/stage-01-a-token-seq.png",
                "assets/waveforms/stage-10-b-result-response.png",
                "token-journey/step-01.png",
                "token-journey/step-10.png",
                "vendor/highlight.min.js",
                "vendor/verilog.min.js",
                "vendor/github-dark.min.css",
                "vendor/LICENSE.highlightjs-BSD-3-Clause",
                "rtl/msh_chip_top.v",
                "rtl/msh_seq.v",
                "rtl/msh_fetch.v",
                "rtl/msh_deq.v",
                "rtl/msh_gemv.v",
                "rtl/msh_vec.v",
                "rtl/msh_kda.v",
                "rtl/msh_mla.v",
                "rtl/msh_mem.v",
                "rtl/msh_lg.v",
                "THIRD_PARTY_NOTICES.md",
                "LICENSE",
                ".nojekyll",
            }
            published = {
                str(path.relative_to(out))
                for path in out.rglob("*")
                if path.is_file()
            }
            self.assertTrue(required <= published, required - published)

            forbidden_suffixes = {".fst", ".lib", ".sucl"}
            self.assertFalse(
                [name for name in published if Path(name).suffix in forbidden_suffixes]
            )
            self.assertFalse(
                [
                    name
                    for name in published
                    if name.startswith(("build/", ".venv/"))
                    or "surfer-web" in name
                ]
            )


if __name__ == "__main__":
    unittest.main()
