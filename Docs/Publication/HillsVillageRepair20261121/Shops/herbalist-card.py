"""Reproduce the herbalist construction card from its original transparent painting."""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageOps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_directory", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()

    manifest = Path(__file__).with_name("construction-cards.json")
    name = json.loads(manifest.read_text(encoding="utf-8"))["cards"]["herbalist"]["image_source"]
    with Image.open(args.source_directory / name) as source:
        image = source.convert("RGBA")
    bounds = image.getchannel("A").point(lambda alpha: 255 if alpha > 16 else 0).getbbox()
    tile = ImageOps.contain(image.crop(bounds), (240, 240), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (256, 256))
    canvas.alpha_composite(tile, ((256 - tile.width) // 2, (256 - tile.height) // 2))
    args.output_directory.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output_directory / "herbalist.png", optimize=True)


if __name__ == "__main__":
    main()
