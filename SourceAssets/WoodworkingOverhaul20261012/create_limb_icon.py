"""Author the inventory icon from the actual woodworking target polygon.

No screenshot or acceptance render. The geometry is the configured bow-limb blank;
wood grain and edge shading are deterministic authored pixels, with no source image.
"""
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
data = json.loads((ROOT / "Content/ColdSteelData/woodworking.json").read_text(encoding="utf-8-sig"))
pattern = next(p for p in data["patterns"] if p["id"] == "bow_limb")
scale = 3
size = (192 * scale, 576 * scale)
points = [(y * 256, (1 - x) * 512) for x, y in pattern["outline"]]
lo = tuple(min(p[i] for p in points) for i in range(2))
hi = tuple(max(p[i] for p in points) for i in range(2))
fit = min((size[0] - 36 * scale) / (hi[0] - lo[0]), (size[1] - 32 * scale) / (hi[1] - lo[1]))
poly = [((x - (lo[0] + hi[0]) / 2) * fit + size[0] / 2, (y - (lo[1] + hi[1]) / 2) * fit + size[1] / 2) for x, y in points]
mask = Image.new("L", size)
ImageDraw.Draw(mask).polygon(poly, fill=255)
wood = Image.new("RGBA", size)
pixels = wood.load()
for y in range(size[1]):
    for x in range(size[0]):
        u, v = x / scale, y / scale
        grain = math.sin(u * .5 + math.sin(v * .023) * 2.1) * .07 + math.sin(u * 1.93 + v * .018) * .025
        shade = .88 + grain + .1 * (1 - u / 192)
        pixels[x, y] = (int(176 * shade), int(120 * shade), int(64 * shade), 255)
wood.putalpha(mask)
edge = ImageDraw.Draw(wood)
edge.line(poly + [poly[0]], fill=(219, 168, 99, 255), width=2 * scale, joint="curve")
icon = wood.resize((192, 576), Image.Resampling.LANCZOS)
destination = ROOT / "Content/ColdSteelData/Icons/woodworked_bow_limb.png"
icon.save(destination)
(Path(__file__).parent / "provenance.json").write_text(json.dumps({
    "source": "woodworking.json patterns[bow_limb].outline",
    "method": "Authored polygon rasterization and deterministic wood grain; transparent background",
    "output": str(destination.relative_to(ROOT)),
    "external_assets": [],
    "dimensions": [192, 576]
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
