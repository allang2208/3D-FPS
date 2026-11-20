"""Match portrait crops by measured interpupillary distance; leave face shape and roll intact."""
import json
import os
import shutil
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
HEAD = ROOT / "SourceAssets/VillageHerbalist/FullBody/HeadR3"
PORTRAITS = HEAD / "UE/Portraits"
STUDIO = HEAD / "Review/Studio"
WIDTH, HEIGHT = 880, 880


def crop(image, eyes, view):
    (lx, ly), (rx, ry) = eyes
    distance = ((rx - lx)**2 + (ry - ly)**2)**.5
    source_per_pixel = distance / (165. if view == "front" else 143.)
    cx, cy = (lx + rx) * .5, (ly + ry) * .5
    # Keep a little space to the left of the nose on the turned portrait.
    tx, ty = (WIDTH * (.50 if view == "front" else .446), HEIGHT * .427)
    x0, y0 = cx - tx * source_per_pixel, cy - ty * source_per_pixel
    bg = image.getpixel((4, 4))
    return image.transform((WIDTH, HEIGHT), Image.Transform.AFFINE,
        (source_per_pixel, 0., x0, 0., source_per_pixel, y0), Image.Resampling.BICUBIC, fillcolor=bg)


def main():
    points = json.loads((STUDIO / "pupil-centres.json").read_text(encoding="utf-8"))
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if source:
        import numpy as np
        import OpenEXR
        report = json.loads((source / "studio-saved-package.json").read_text(encoding="utf-8"))
    for view in ("front", "three-quarter"):
        for key in ("FaceR2", "HeadR3"):
            stem = key + "-" + view
            if source:
                with OpenEXR.File(str(source / (stem + ".exr"))) as scene:
                    channels = scene.channels()
                    color = channels.get("RGBA") or channels["RGB"]
                    linear = np.clip(color.pixels[:, :, :3].astype(np.float32), 0., 1.)
                srgb = np.where(linear <= .0031308, linear * 12.92, 1.055 * linear**(1./2.4) - .055)
                image = Image.fromarray(np.rint(srgb*255.).astype(np.uint8))
                temp = PORTRAITS / (stem + ".png.tmp")
                image.save(temp, format="PNG")
                os.replace(temp, PORTRAITS / (stem + ".png"))
            else:
                image = Image.open(STUDIO / (stem + ".png")).convert("RGB")
            crop(image, points[view][key], view).save(PORTRAITS / (key + "-" + view + "-matched.png"))
    if source:
        shutil.copyfile(STUDIO / "pupil-centres.json", PORTRAITS / "pupil-centres.json")
        for key, row in report.items():
            row["views"] = {Path(f).stem + ".png": value for f, value in row["views"].items()}
            row["capture"] = "Softbox studio; final tone-curve HDR converted to sRGB"
            (PORTRAITS / (key + "-saved-package.json")).write_text(
                json.dumps({key: row}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
