"""Version cards must remain accurate and fit the social preview canvas."""
from contextlib import redirect_stdout, redirect_stderr
from io import BytesIO, StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_share_cards as cards


def png_bytes(color="#f6f3eb", size=(1200, 630)):
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


class ShareCardTests(unittest.TestCase):
    def fixture(self, root):
        (root / "assets").mkdir()
        (root / "assets/update-share-base.png").write_bytes(png_bytes())
        (root / "data").mkdir()
        data = {"releases": [{"version": version, "date": "2026-10-06",
                "title": "Release", "summary": "Update", "source": "editorial",
                "sections": [{"title": "Changes", "items": ["New feature"]}]}
                for version in ("1.1.0", "1.0.0")]}
        (root / "data/releases.json").write_text(json.dumps(data), encoding="utf-8")

    def test_versions_have_distinct_pixels_and_preserve_brand_region(self):
        base = png_bytes()
        first = Image.open(BytesIO(cards.render_card(base, "1.1.0")))
        second = Image.open(BytesIO(cards.render_card(base, "1.0.0")))
        self.assertEqual(first.size, (1200, 630))
        self.assertEqual(first.format, "PNG")
        self.assertIsNotNone(ImageChops.difference(first, second).getbbox())
        original = Image.open(BytesIO(base))
        self.assertIsNone(ImageChops.difference(first.crop((0, 0, 1200, 200)),
                                              original.crop((0, 0, 1200, 200))).getbbox())

    def test_longest_version_fits_inside_number_region(self):
        base = png_bytes()
        card = Image.open(BytesIO(cards.render_card(base, "999999.999999.999999")))
        bounds = ImageChops.difference(card, Image.open(BytesIO(base))).getbbox()
        self.assertIsNotNone(bounds)
        left, top, right, bottom = bounds
        self.assertGreaterEqual(left, 78)
        self.assertGreaterEqual(top, 245)
        self.assertLessEqual(right, 1122)
        self.assertLessEqual(bottom, 480)

    def test_rejects_invalid_versions_and_wrong_base_dimensions(self):
        for version in ("../1", "01.0", "1.0.0.0", "1<script>", "1/2"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                cards.render_card(png_bytes(), version)
        with self.assertRaises(ValueError):
            cards.render_card(png_bytes(size=(100, 100)), "1.1.0")

    def test_build_and_check_detect_changed_base_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            self.assertFalse(cards.build_cards(root, check=True))
            self.assertFalse((root / "assets/updates").exists())
            self.assertTrue(cards.build_cards(root))
            self.assertTrue(cards.build_cards(root, check=True))
            destination = root / "assets/updates/1.1.0-v1.png"
            initial = destination.read_bytes()
            self.assertTrue((root / "assets/updates/1.0.0-v1.png").is_file())
            (root / "assets/update-share-base.png").write_bytes(png_bytes("#ffffff"))
            self.assertFalse(cards.build_cards(root, check=True))
            self.assertEqual(destination.read_bytes(), initial)
            self.assertTrue(cards.build_cards(root))
            self.assertNotEqual(destination.read_bytes(), initial)
            self.assertTrue(cards.build_cards(root, check=True))
            self.assertTrue(cards.build_cards(root))

    def test_refuses_symlink_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            (root / "assets/updates").symlink_to(elsewhere, target_is_directory=True)
            with self.assertRaises(ValueError):
                cards.build_cards(root)
            self.assertFalse(list(elsewhere.iterdir()))

    def test_cli_reports_success_stale_and_invalid_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            with patch.object(cards, "ROOT", root), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(cards.main(["--check"]), 1)
                self.assertEqual(cards.main([]), 0)
                self.assertEqual(cards.main(["--check"]), 0)
                (root / "data/releases.json").write_text("{}", encoding="utf-8")
                self.assertEqual(cards.main([]), 1)


if __name__ == "__main__":
    unittest.main()
