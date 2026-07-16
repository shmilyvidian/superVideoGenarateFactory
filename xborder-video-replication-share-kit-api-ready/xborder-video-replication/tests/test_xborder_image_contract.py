import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import xborder_image as xi  # noqa: E402

ONE_PIXEL_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc"
    b"\xff\x1f\x00\x03\x03\x02\x00\xef\xbf\xa7\xdb\x00\x00\x00\x00IEND"
    b"\xaeB`\x82"
)


class XBorderImageContractTest(unittest.TestCase):
    def test_build_body_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            p1 = tmp_path / "prod.png"; p1.write_bytes(ONE_PIXEL_PNG)
            p2 = tmp_path / "prev.png"; p2.write_bytes(ONE_PIXEL_PNG)
            args = types.SimpleNamespace(
                prompt="cell 1", prompt_file=None,
                reference_image=[p1, p2],
                model="seedream-4.5", scale="9:16",
            )
            body = xi.build_body(args)
            self.assertEqual(len(body["image"]), 2)
            self.assertTrue(body["image"][0].startswith("data:image/"))
            self.assertEqual(body["model"], "seedream-4.5")
            self.assertEqual(body["seedreamOptions"]["aspect_ratio"], "9:16")

    def test_nano_banana_omits_seedream_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "prod.png"; p1.write_bytes(ONE_PIXEL_PNG)
            args = types.SimpleNamespace(
                prompt="c", prompt_file=None, reference_image=[p1],
                model="nano-banana-pro", scale="9:16",
            )
            body = xi.build_body(args)
            self.assertNotIn("seedreamOptions", body)

    def test_dry_run_needs_no_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            p1 = tmp_path / "prod.png"; p1.write_bytes(ONE_PIXEL_PNG)
            out = tmp_path / "frame.png"
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / "xborder_image.py"),
                 "--prompt", "c", "--reference-image", str(p1),
                 "--output", str(out), "--dry-run"],
                check=False, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
