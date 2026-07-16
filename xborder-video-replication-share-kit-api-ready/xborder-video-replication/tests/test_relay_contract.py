import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import seedance_submit as ss  # noqa: E402

ONE_PIXEL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc"
    b"\xff\x1f\x00\x03\x03\x02\x00\xef\xbf\xa7\xdb\x00\x00\x00\x00IEND"
    b"\xaeB`\x82"
)


class RelayContractTest(unittest.TestCase):
    def test_tasks_path_is_relay_video_route(self):
        self.assertEqual(ss.TASKS_PATH, "/video/seedance/tasks")

    def test_default_base_url_is_prod_relay(self):
        self.assertEqual(ss.DEFAULT_BASE_URL, "https://n11-server.lfy071.workers.dev")

    def test_build_task_url_uses_relay(self):
        base = "https://n11-server.lfy071.workers.dev"
        self.assertEqual(
            ss.build_task_url(base), base + "/video/seedance/tasks"
        )
        self.assertEqual(
            ss.build_task_url(base, "pred-1"), base + "/video/seedance/tasks/pred-1"
        )

    def test_no_ark_api_key_symbols(self):
        src = (SCRIPTS / "seedance_submit.py").read_text(encoding="utf-8")
        self.assertNotIn("ARK_API_KEY", src)
        self.assertNotIn("seedance.env", src)

    def test_dry_run_needs_no_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ref = tmp_path / "grid.png"
            ref.write_bytes(ONE_PIXEL_PNG)
            out = tmp_path / "out"
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "seedance_submit.py"),
                 "--prompt", "t", "--reference-image", str(ref),
                 "--reference-mode", "grid-storyboard",
                 "--output-dir", str(out), "--duration", "9",
                 "--resolution", "480p", "--dry-run"],
                check=False, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((out / "request.redacted.json").exists())

    def test_dry_run_payload_is_replicate_input(self):
        import json as _json
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            ref = tmp_path / "grid.png"; ref.write_bytes(ONE_PIXEL_PNG)
            out = tmp_path / "out"
            subprocess.run(
                [sys.executable, str(SCRIPTS / "seedance_submit.py"),
                 "--prompt", "t", "--reference-image", str(ref),
                 "--reference-mode", "grid-storyboard", "--output-dir", str(out),
                 "--ratio", "9:16", "--duration", "9", "--resolution", "480p", "--dry-run"],
                check=True, text=True, capture_output=True,
            )
            payload = _json.loads((out / "request.redacted.json").read_text(encoding="utf-8"))
            self.assertIsInstance(payload["reference_images"], list)
            self.assertEqual(payload["aspect_ratio"], "9:16")
            self.assertIn("generate_audio", payload)
            self.assertNotIn("content", payload)
            self.assertNotIn("model", payload)


if __name__ == "__main__":
    unittest.main()
