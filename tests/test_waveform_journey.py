from pathlib import Path
import re
import struct
import unittest


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "docs" / "nano-kpu-rtl-architecture.html"
WAVE_DIR = ROOT / "docs" / "assets" / "waveforms"

EXPECTED_BY_STAGE = [
    [
        "stage-01-a-token-seq.png",
        "stage-01-b-seq-fetch.png",
        "stage-01-c-fetch-deq.png",
        "stage-01-d-deq-xbuf.png",
    ],
    ["stage-02-a-seq-vec-request.png", "stage-02-b-vec-xbuf-write.png"],
    [
        "stage-03-a-sequencer-schedule.png",
        "stage-03-b-seq-fetch.png",
        "stage-03-c-fetch-gemv.png",
        "stage-03-d-gemv-xbuf.png",
    ],
    ["stage-04-a-vec-preprocess.png", "stage-04-b-kda-xbuf.png"],
    [
        "stage-05-a-sequencer-schedule.png",
        "stage-05-b-gemv-projection.png",
        "stage-05-c-vec-moe-write.png",
    ],
    [
        "stage-06-a-sequencer-schedule.png",
        "stage-06-b-seq-fetch.png",
        "stage-06-c-fetch-gemv.png",
        "stage-06-d-gemv-xbuf.png",
    ],
    ["stage-07-a-mla-request-fsm.png", "stage-07-b-mla-xbuf.png"],
    [
        "stage-08-a-sequencer-schedule.png",
        "stage-08-b-gemv-projection.png",
        "stage-08-c-vec-moe-write.png",
    ],
    [
        "stage-09-a-final-norm.png",
        "stage-09-b-lm-head-gemv.png",
        "stage-09-c-logit-write.png",
    ],
    ["stage-10-a-logit-scan.png", "stage-10-b-result-response.png"],
]
EXPECTED = [name for stage in EXPECTED_BY_STAGE for name in stage]


class WaveformJourneyTests(unittest.TestCase):
    def test_all_surfer_capture_assets_are_valid(self):
        for name in EXPECTED:
            path = WAVE_DIR / name
            self.assertTrue(path.is_file(), name)
            data = path.read_bytes()
            self.assertEqual(b"\x89PNG\r\n\x1a\n", data[:8], name)
            width, height = struct.unpack(">II", data[16:24])
            self.assertEqual((1600, 900), (width, height), name)
            self.assertGreater(path.stat().st_size, 60_000, name)

    def test_journey_references_every_waveform_once(self):
        html = HTML.read_text()
        refs = re.findall(r"assets/waveforms/(stage-[^'\"]+\.png)", html)
        self.assertEqual(EXPECTED, refs)

    def test_each_stage_has_a_readable_multi_capture_evidence_gallery(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn('id="waveformGallery"', html)
        self.assertIn("className='waveCaptureCard'", html)
        self.assertIn("capture.instance", html)
        self.assertIn("capture.signals", html)
        self.assertIn("capture.evidence", html)
        self.assertIn("capture.window", html)
        self.assertEqual(10, html.count("captures:["))
        for captures in EXPECTED_BY_STAGE:
            self.assertGreaterEqual(len(captures), 2)
            self.assertLessEqual(len(captures), 4)

    def test_embedding_gallery_covers_complete_module_path(self):
        html = HTML.read_text(encoding="utf-8")
        for module in ("msh_tok", "msh_seq", "msh_fetch", "msh_deq", "msh_xbuf"):
            self.assertIn(module, html)
        for handoff in (
            "msh_tok → msh_seq",
            "msh_seq → msh_fetch",
            "msh_fetch → msh_deq",
            "msh_deq → msh_xbuf",
        ):
            self.assertIn(handoff, html)

    def test_journey_exposes_waveform_evidence_ui(self):
        html = HTML.read_text()
        for element_id in (
            "waveformGallery",
            "waveformWindow",
            "waveformToken",
            "waveformInstance",
            "waveformSignals",
            "waveformEvidence",
        ):
            self.assertIn(f'id="{element_id}"', html)
        self.assertIn("Surfer waveform evidence", html)
        for window in (
            "33.278–33.300 ns",
            "33.286–33.405 ns",
            "33.290–33.442 ns",
            "33.292–33.605 ns",
            "354.920–355.208 ns",
            "355.200–355.220 ns",
        ):
            self.assertIn(window, html)
        self.assertIn("rsp_data=0x0000d0de", html)

    def test_mobile_journey_keeps_waveform_evidence_accessible(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn(".journeyDeck .sideCard{display:block", html)
        self.assertIn(".journeyDeck{display:block;overflow-y:auto", html)

    def test_journey_switches_one_visual_at_a_time_and_groups_captures(self):
        html = HTML.read_text(encoding="utf-8")
        for element_id in (
            "showDiagram",
            "showWaveform",
            "diagramPanel",
            "waveformPanel",
            "waveformGallery",
        ):
            self.assertIn(f'id="{element_id}"', html)
        self.assertIn(".visualPanel[hidden]{display:none}", html)
        self.assertIn(".waveCaptureModules{display:flex", html)
        self.assertIn(".waveformGallery{min-height:0;overflow:auto;padding:12px;display:flex", html)
        self.assertIn(".waveCaptureCard{flex:0 0 auto", html)
        self.assertIn("function setJourneyVisual(mode)", html)
        self.assertIn("function renderCaptureGallery(captures,stepTitle)", html)
        self.assertEqual(10, html.count("captures:["))


if __name__ == "__main__":
    unittest.main()
