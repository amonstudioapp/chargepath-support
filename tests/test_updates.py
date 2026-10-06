"""Release publishing contract: safe content, immutable history, reproducible pages."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_updates as build
import sync_app_store as sync


def release(version="1.2.0", **changes):
    return {"version": version, "date": "2026-10-06", "title": "更新 <安全>",
            "summary": "體驗 & 紀錄", "source": "editorial",
            "highlights": [{"title": "快速", "description": "更快紀錄"}],
            "sections": [{"title": "本次更新", "items": ["新增紀錄"]}], **changes}


def payload(**changes):
    return {"resultCount": 1, "results": [{"trackId": 6809342215,
            "bundleId": "tw.local.chargepath", "version": "1.3.0",
            "currentVersionReleaseDate": "2026-10-05T18:30:00Z",
            "releaseNotes": "更新摘要\n• 改善充電紀錄\n- 修正顯示", **changes}]}


class ValidationTests(unittest.TestCase):
    def test_numeric_order_and_input_immutability(self):
        data = {"releases": [release("1.9.0"), release("1.10.0")]}
        before = copy.deepcopy(data)
        self.assertEqual([r["version"] for r in build.validate_data(data)], ["1.10.0", "1.9.0"])
        self.assertEqual(data, before)

    def test_invalid_versions(self):
        for value in ("../../bad", "01.2.3", "1.2.3.4", "1.2.3/", "1.2.3\n", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build.validate_data({"releases": [release(value)]})

    def test_one_to_three_version_components_sort_and_keep_urls(self):
        records = build.validate_data({"releases": [release("2"), release("2.1"), release("1.99.99")]})
        self.assertEqual([item["version"] for item in records], ["2.1", "2", "1.99.99"])
        self.assertIn('./2.1/', build.render_row(records[0]))
        with self.assertRaises(ValueError):
            build.validate_data({"releases": [release("2.1"), release("2.1.0")]})

    def test_rejects_bad_content(self):
        invalid = [None, {}, {"releases": []}, {"releases": [release(), release()]},
                   {"releases": [release(date="2026-02-30")]},
                   {"releases": [release(date="2026-1-1")]},
                   {"releases": [release(title=" ")]},
                   {"releases": [release(summary="x" * 10001)]},
                   {"releases": [release(source="external")]},
                   {"releases": [release(sections=[])]},
                   {"releases": [release(sections=[{"title": "a", "items": []}])]},
                   {"releases": [release(highlights=[{"title": "a"}])]},
                   {"releases": [release(sourceNote="bad\x00content")]},
                   {"releases": [release(extra="unsupported")]},
                   {"releases": ["bad"]}]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                build.validate_data(value)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        (self.root / "templates").mkdir()
        (self.root / "templates/updates-index.html").write_text(
            "$latest_version|$latest_date|$latest_title|$latest_summary|$latest_url|$latest_highlights|$release_list")
        (self.root / "templates/update-detail.html").write_text(
            "$version|$date|$title|$summary|$highlights|$sections|$source_note|$previous_link|$next_link|$canonical")
        self.data = {"releases": [release(), release("1.1.0", highlights=[], sourceNote='A <script>alert("x")</script>')]}
        (self.root / "data/releases.json").write_text(json.dumps(self.data))

    def test_build_pages_links_rss_escaping_and_freshness(self):
        self.assertFalse(build.build_site(self.root, check=True))
        self.assertFalse((self.root / "updates").exists())
        self.assertTrue(build.build_site(self.root))
        self.assertTrue(build.build_site(self.root, check=True))
        index = (self.root / "updates/index.html").read_text()
        detail = (self.root / "updates/1.1.0/index.html").read_text()
        self.assertIn("2026 年 10 月 6 日", index)
        self.assertIn("&lt;安全&gt;", index)
        self.assertIn("體驗 &amp; 紀錄", index)
        self.assertIn('./1.2.0/', index)
        self.assertIn('../1.2.0/', detail)
        self.assertNotIn('<script>', detail)
        rss = ET.parse(self.root / "updates/feed.xml")
        self.assertEqual(len(rss.findall("./channel/item")), 2)
        self.assertEqual(rss.findtext("./channel/item/link"), build.BASE_URL + "/updates/1.2.0/")
        (self.root / "updates/index.html").write_text("stale")
        self.assertFalse(build.build_site(self.root, check=True))
        self.assertEqual((self.root / "updates/index.html").read_text(), "stale")

    def test_cli_reports_failures_and_check(self):
        with patch.object(build, "ROOT", self.root):
            self.assertEqual(build.main(["--check"]), 1)
            self.assertEqual(build.main([]), 0)
            self.assertEqual(build.main(["--check"]), 0)
            (self.root / "data/releases.json").write_text("broken")
            self.assertEqual(build.main([]), 1)

    def test_stale_generated_pages_checked_and_pruned_preserving_unknown_files(self):
        build.build_site(self.root)
        stale_page = self.root / "updates/1.1.0/index.html"
        extra_asset = stale_page.parent / "photo.png"
        extra_asset.write_bytes(b"keep asset")
        unknown_page = self.root / "updates/3.0.0/index.html"
        unknown_page.parent.mkdir()
        unknown_page.write_text("Manually maintained page")
        unknown_directory = self.root / "updates/archive/index.html"
        unknown_directory.parent.mkdir()
        unknown_directory.write_text(stale_page.read_text())
        outside = self.root / "outside"
        outside.mkdir()
        outside_page = outside / "index.html"
        outside_page.write_text(stale_page.read_text())
        linked_directory = self.root / "updates/4.0.0"
        linked_directory.symlink_to(outside, target_is_directory=True)
        linked_file = self.root / "updates/5.0.0/index.html"
        linked_file.parent.mkdir()
        linked_file.symlink_to(outside_page)
        (self.root / "data/releases.json").write_text(json.dumps({"releases": [self.data["releases"][0]]}))
        build.build_site(self.root)
        self.assertFalse(stale_page.exists())
        self.assertEqual(extra_asset.read_bytes(), b"keep asset")
        self.assertEqual(unknown_page.read_text(), "Manually maintained page")
        self.assertTrue(unknown_directory.exists())
        self.assertTrue(linked_directory.is_symlink())
        self.assertTrue(linked_file.is_symlink())
        self.assertTrue(outside_page.exists())
        self.assertTrue(build.build_site(self.root, check=True))

    def test_stale_page_alone_causes_check_failure_without_mutation(self):
        build.build_site(self.root)
        stale_html = (self.root / "updates/1.1.0/index.html").read_text()
        (self.root / "data/releases.json").write_text(json.dumps({"releases": [self.data["releases"][0]]}))
        build.build_site(self.root)
        stale_page = self.root / "updates/1.1.0/index.html"
        stale_page.parent.mkdir(exist_ok=True)
        stale_page.write_text(stale_html)
        self.assertFalse(build.build_site(self.root, check=True))
        self.assertEqual(stale_page.read_text(), stale_html)
        build.build_site(self.root)
        self.assertFalse(stale_page.parent.exists())


class SyncTests(unittest.TestCase):
    def test_public_fields_taipei_date_and_notes(self):
        data = {"releases": [release()]}
        before = copy.deepcopy(data)
        result, changed = sync.merge_payload(data, payload(secret="never persist"))
        self.assertTrue(changed)
        latest = result["releases"][0]
        self.assertEqual(latest["date"], "2026-10-06")
        self.assertEqual(latest["summary"], "更新摘要")
        self.assertEqual(latest["sections"][0]["items"], ["改善充電紀錄", "修正顯示"])
        self.assertNotIn("secret", latest)
        self.assertEqual(data, before)

    def test_same_version_and_older_never_overwrite(self):
        for source in ("editorial", "app-store"):
            data = {"releases": [release(source=source)]}
            for version in ("1.2.0", "1.1.0"):
                result, changed = sync.merge_payload(data, payload(version=version))
                self.assertFalse(changed)
                self.assertEqual(result, data)

    def test_missing_notes_single_line_notes_and_empty_history(self):
        for notes in (None, "", " \n\t ", "•\n-", "一行說明"):
            result, changed = sync.merge_payload({"releases": []}, payload(releaseNotes=notes))
            self.assertTrue(changed)
            self.assertTrue(result["releases"][0]["sections"][0]["items"])

    def test_identity_dates_and_shape_fail_closed(self):
        invalid = [None, {}, {"resultCount": 0, "results": []},
                   {"resultCount": 1, "results": [None]},
                   payload(trackId=1), payload(bundleId="wrong"),
                   payload(version="../../"), payload(currentVersionReleaseDate="bad"),
                   payload(currentVersionReleaseDate="2026-10-05T00:00:00"),
                   payload(releaseNotes=123)]
        for item in invalid:
            with self.subTest(item=item), self.assertRaises(ValueError):
                sync.merge_payload({"releases": []}, item)

    def test_fetch_limits_timeout_and_json(self):
        response = io.BytesIO(json.dumps(payload()).encode())
        with patch.object(sync, "urlopen", return_value=response) as opener:
            self.assertEqual(sync.fetch_payload()["resultCount"], 1)
            self.assertEqual(opener.call_args.kwargs["timeout"], 20)
        with patch.object(sync, "urlopen", return_value=io.BytesIO(b"x" * (sync.MAX_RESPONSE_BYTES + 1))):
            with self.assertRaises(ValueError):
                sync.fetch_payload()

    def test_cli_atomic_update_dry_run_and_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            content = root / "data/releases.json"
            content.write_text(json.dumps({"releases": [release()]}))
            fixture = root / "lookup.json"
            fixture.write_text(json.dumps(payload()))
            original = content.read_bytes()
            with patch.object(sync, "ROOT", root):
                self.assertEqual(sync.main(["--input", str(fixture), "--dry-run"]), 0)
                self.assertEqual(content.read_bytes(), original)
                self.assertEqual(sync.main(["--input", str(fixture)]), 0)
                self.assertEqual(json.loads(content.read_text())["releases"][0]["version"], "1.3.0")
                self.assertEqual(sync.main(["--input", str(fixture)]), 0)
                fixture.write_text("invalid")
                self.assertEqual(sync.main(["--input", str(fixture)]), 1)
                with patch.object(sync, "fetch_payload", return_value=payload(version="1.4.0")):
                    self.assertEqual(sync.main([]), 0)
            self.assertFalse(list((root / "data").glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
