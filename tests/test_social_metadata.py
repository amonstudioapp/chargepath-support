"""Social crawlers must receive a complete preview without executing JavaScript."""
from html.parser import HTMLParser
import json
from pathlib import Path
import struct
import sys
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_updates as build

IMAGE_URL = build.BASE_URL + "/assets/chargepath-share-v1.png"


class HeadMetadata(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.in_head = False
        self.meta = {}
        self.canonicals = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "head":
            self.in_head = True
        elif self.in_head and tag == "meta":
            key = values.get("property") or values.get("name")
            self.meta.setdefault(key, []).append(values.get("content", ""))
        elif self.in_head and tag == "link" and values.get("rel") == "canonical":
            self.canonicals.append(values.get("href", ""))

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False


class SocialMetadataTests(unittest.TestCase):
    def pages(self):
        data = json.loads((ROOT / "data/releases.json").read_text(encoding="utf-8"))
        rendered = build.render_site(ROOT, build.validate_data(data))
        return {"index.html": (ROOT / "index.html").read_text(encoding="utf-8"),
                **{path: html for path, html in rendered.items() if path.endswith(".html")}}

    def test_static_preview_metadata_on_home_index_and_every_release(self):
        expected = {
            "og:image:width": "1200",
            "og:image:height": "630",
            "og:image:type": "image/png",
            "og:site_name": "電程 Dency",
            "og:locale": "zh_TW",
            "twitter:card": "summary_large_image",
        }
        releases = build.validate_data(json.loads((ROOT / "data/releases.json").read_text()))
        for path, html in self.pages().items():
            with self.subTest(page=path):
                head = HeadMetadata(html)
                version = path.split("/")[1] if path.count("/") == 2 else releases[0]["version"]
                image_url = IMAGE_URL if path == "index.html" else f"{build.BASE_URL}/assets/updates/{version}-v1.png"
                for key in ("og:image", "og:image:secure_url", "twitter:image"):
                    self.assertEqual(head.meta.get(key), [image_url])
                if path != "index.html":
                    self.assertIn(version, head.meta["og:image:alt"][0])
                for key, value in expected.items():
                    self.assertEqual(head.meta.get(key), [value], f"{path}: {key}")
                for key in ("og:title", "og:description", "og:image:alt"):
                    values = head.meta.get(key, [])
                    self.assertEqual(len(values), 1, f"{path}: {key}")
                    self.assertTrue(values[0].strip(), f"{path}: empty {key}")
                canonical = build.BASE_URL + "/" + path.removesuffix("index.html")
                self.assertEqual(head.canonicals, [canonical])
                self.assertEqual(head.meta.get("og:url"), [canonical])

    def test_preview_image_is_local_lightweight_landscape_png(self):
        url = urlsplit(IMAGE_URL)
        base = urlsplit(build.BASE_URL)
        self.assertEqual(url.scheme, "https")
        self.assertEqual(url.netloc, base.netloc)
        relative = url.path.removeprefix(base.path + "/")
        image_path = ROOT / relative
        self.assertTrue(image_path.is_file(), f"Missing share image: {relative}")
        image = image_path.read_bytes()
        self.assertLess(len(image), 1_000_000)
        self.assertEqual(image[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(image[12:16], b"IHDR")
        self.assertEqual(struct.unpack(">II", image[16:24]), (1200, 630))


if __name__ == "__main__":
    unittest.main()
