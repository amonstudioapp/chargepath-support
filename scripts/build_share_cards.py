#!/usr/bin/env python3
"""Build deterministic version-number share cards from the Dency brand base."""
import argparse
from io import BytesIO
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont

from build_updates import validate_data, version_key

ROOT = Path(__file__).resolve().parents[1]
CANVAS_SIZE = (1200, 630)


def render_card(base_bytes, version):
    """Return a PNG with a validated version fitted into the reserved number area."""
    version_key(version)
    with Image.open(BytesIO(base_bytes)) as source:
        if source.size != CANVAS_SIZE:
            raise ValueError("Share card base must be 1200 × 630 pixels")
        card = source.convert("RGB")
    draw = ImageDraw.Draw(card)
    size = 240
    while True:
        font = ImageFont.load_default(size=size)
        left, top, right, bottom = draw.textbbox((0, 0), version, font=font)
        if right - left <= 1044 and bottom - top <= 235:
            break
        size -= 1
    draw.text((78 - left, 245 - top), version, font=font, fill="#193f32")
    output = BytesIO()
    card.save(output, format="PNG", optimize=True)
    return output.getvalue()


def build_cards(root=ROOT, check=False):
    root = Path(root)
    releases = validate_data(json.loads((root / "data/releases.json").read_text(encoding="utf-8")))
    base = (root / "assets/update-share-base.png").read_bytes()
    output_directory = root / "assets/updates"
    if output_directory.is_symlink() or (root / "assets").is_symlink():
        raise ValueError("Share card output directory must not be a symlink")
    fresh = True
    for release in releases:
        destination = output_directory / f'{release["version"]}-v1.png'
        if destination.is_symlink():
            raise ValueError("Share card output must not be a symlink")
        content = render_card(base, release["version"])
        matches = destination.is_file() and destination.read_bytes() == content
        if check:
            fresh = fresh and matches
        elif not matches:
            output_directory.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
    return fresh


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check generated images without writing")
    args = parser.parse_args(argv)
    try:
        if not build_cards(ROOT, check=args.check):
            print("Share cards need rebuilding: python3 scripts/build_share_cards.py", file=sys.stderr)
            return 1
    except (OSError, ValueError, KeyError) as error:
        print(f"Cannot build share cards: {error}", file=sys.stderr)
        return 1
    print("Share cards are current." if args.check else "Share cards built.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
