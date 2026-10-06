#!/usr/bin/env python3
"""Import only a newly published Dency version from Apple's Taiwan listing."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from build_updates import ROOT, plain_text, validate_data, version_key

LOOKUP_URL = "https://itunes.apple.com/lookup?id=6809342215&country=tw"
APP_ID = 6809342215
MAX_RESPONSE_BYTES = 1024 * 1024
FALLBACK_NOTES = "這次更新的詳細說明，請參閱 App Store。"


def fetch_payload():
    with urlopen(LOOKUP_URL, timeout=20) as response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise ValueError("App Store response exceeds the size limit")
    return json.loads(body)


def release_from_payload(payload):
    if (not isinstance(payload, dict) or payload.get("resultCount") != 1
            or not isinstance(payload.get("results"), list) or len(payload["results"]) != 1):
        raise ValueError("App Store must return exactly one app")
    app = payload["results"][0]
    if not isinstance(app, dict) or app.get("trackId") != APP_ID:
        raise ValueError("Unexpected App Store app identity")
    if "bundleId" in app and app["bundleId"] != "tw.local.chargepath":
        raise ValueError("Unexpected App Store bundle identity")
    version = app.get("version")
    version_key(version)
    timestamp = app.get("currentVersionReleaseDate")
    if not isinstance(timestamp, str):
        raise ValueError("Missing App Store release date")
    published = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if published.tzinfo is None:
        raise ValueError("App Store release date must include its time zone")
    notes = app.get("releaseNotes")
    if notes is None or (isinstance(notes, str) and not notes.strip()):
        notes = FALLBACK_NOTES
    plain_text(notes, "App Store release notes", 50000)
    stripped = [re.sub(r"^[•●▪\-*]\s*", "", line.strip()) for line in notes.splitlines()]
    lines = [line for line in stripped if line] or [FALLBACK_NOTES]
    summary = lines[0]
    entry = {"version": version, "date": published.astimezone(ZoneInfo("Asia/Taipei")).date().isoformat(),
             "title": f"電程 {version} 更新", "summary": summary, "source": "app-store",
             "sections": [{"title": "本次更新", "items": lines[1:] or lines}],
             "sourceNote": "更新說明取自台灣 App Store；實際功能與可用性以 App 內顯示為準。"}
    validate_data({"releases": [entry]})
    return entry


def merge_payload(data, payload):
    existing = validate_data(data, allow_empty=True)
    entry = release_from_payload(payload)
    if existing and version_key(entry["version"]) <= version_key(existing[0]["version"]):
        return data, False
    merged = {"releases": [entry, *existing]}
    validate_data(merged)
    return merged, True


def atomic_write(path, data):
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Read an Apple lookup JSON fixture instead of the network")
    parser.add_argument("--dry-run", action="store_true", help="Report a new version without writing")
    args = parser.parse_args(argv)
    try:
        path = ROOT / "data/releases.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        payload = json.loads(args.input.read_text(encoding="utf-8")) if args.input else fetch_payload()
        merged, changed = merge_payload(data, payload)
        if changed and not args.dry_run:
            atomic_write(path, merged)
        print(f'New version: {merged["releases"][0]["version"]}' if changed else "No new App Store version.")
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f"Cannot sync App Store: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
