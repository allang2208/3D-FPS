"""Compare Lin Zhi's design with the saved old and new UE meshes at the same pupil spacing."""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
HEAD = ROOT / "SourceAssets/VillageHerbalist/FullBody/HeadR3"
REVIEW = HEAD / "Review"
PORTRAITS = REVIEW / "Studio"


def crop_portrait(path, pupils, view):
    image = Image.open(path).convert("RGB")
    (left_x, left_y), (right_x, right_y) = pupils
    width, height = 392, (424 if view == "front" else 450)
    target_distance = 83 if view == "front" else 76
    source_per_pixel = math.hypot(right_x - left_x, right_y - left_y) / target_distance
    target_x = width * (.5 if view == "front" else .345)
    x0 = (left_x + right_x) / 2 - target_x * source_per_pixel
    target_y = 183 if view == "front" else 200
    y0 = (left_y + right_y) / 2 - target_y * source_per_pixel
    return image.transform((width, height), Image.Transform.AFFINE,
                           (source_per_pixel, 0, x0, 0, source_per_pixel, y0),
                           Image.Resampling.BICUBIC, fillcolor=image.getpixel((2, 2)))


def develop_studio(source):
    """Convert UE's tone-mapped linear Rec.709 render targets to display sRGB."""
    import numpy as np
    import OpenEXR

    for view in ("front", "three-quarter"):
        for revision in ("FaceR2", "HeadR3"):
            stem = f"{revision}-{view}"
            with OpenEXR.File(str(source / (stem + ".exr"))) as scene:
                channels = scene.channels()
                rgb = channels.get("RGBA") or channels["RGB"]
                linear = np.maximum(rgb.pixels[:, :, :3].astype("float32"), 0.)
            srgb = np.where(linear <= .0031308, 12.92 * linear, 1.055 * linear ** (1 / 2.4) - .055)
            output = np.clip(srgb * 255. + .5, 0., 255.).astype("uint8")
            Image.fromarray(output).save(PORTRAITS / (stem + ".png"))


def main():
    points = json.loads((PORTRAITS / "pupil-centres.json").read_text(encoding="utf-8"))
    original = HEAD / "References/Original_Front.png"
    references = {
        "front": (original, ((242, 266), (355, 266)), "原始角色设定"),
        "three-quarter": (HEAD / "References/02_three_quarter.png",
                          points["three-quarter"]["reference"], "本次无镜头部设定"),
    }
    REVIEW.mkdir(exist_ok=True)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    for view, reference in references.items():
        rows = [reference]
        for revision, label in (("FaceR2", "旧模型 · UE"), ("HeadR3", "新模型 · UE")):
            rows.append((PORTRAITS / f"{revision}-{view}.png", points[view][revision], label))
        height = 424 if view == "front" else 450
        canvas = Image.new("RGB", (1197, height + 54), (34, 34, 33))
        draw = ImageDraw.Draw(canvas)
        for index, (path, pupils, label) in enumerate(rows):
            x = 5 + index * 397
            canvas.paste(crop_portrait(path, pupils, view), (x, 5))
            draw.text((x + 10, height + 13), label, font=font, fill=(235, 231, 225))
        canvas.save(REVIEW / f"{view}-comparison.jpg", quality=94, subsampling=0)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        develop_studio(Path(sys.argv[1]))
    main()
