"""Tile review renders: py sheet.py <dir> <cols> <width> <out.jpg> [crop x0 y0 x1 y1] — labels from measure.json."""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main():
    d, cols, width, out = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    crop = tuple(int(v) for v in sys.argv[5:9]) if len(sys.argv) > 8 else None
    rows = json.loads((d / 'measure.json').read_text())
    font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 20)
    tiles = []
    for r in rows:
        im = Image.open(d / f"f{r['frame']:04d}.png").convert('RGB')
        if crop:
            im = im.crop(crop)
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        dr = ImageDraw.Draw(im)
        dr.rectangle((0, im.height - 28, 210, im.height), fill=(0, 0, 0))
        dr.text((6, im.height - 26), f"{r['t']:.3f}s  {r['blade_screen_deg']:.0f}°", font=font, fill=(255, 255, 0))
        tiles.append(im)
    h = tiles[0].height
    sheet = Image.new('RGB', (cols * width, ((len(tiles) + cols - 1) // cols) * h), (20, 20, 20))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * width, (i // cols) * h))
    sheet.save(d.parent / out, quality=90)
    print(out, len(tiles))


if __name__ == '__main__':
    main()
