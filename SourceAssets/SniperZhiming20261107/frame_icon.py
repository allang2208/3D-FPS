"""Set the orthographic model render into the existing gunsmith's riveted frame."""
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter, ImageOps


HERE = Path(__file__).resolve().parent
FRAMES = HERE.parents[1] / "Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms"


def compose(subject):
    frame = Image.open(FRAMES / "tactical_false.png").convert("RGBA")
    graphite = ImageOps.grayscale(Image.open(HERE.parent / "FirearmFramedIcons20260930/muzzle_brake_framed_v2.png"))
    width, height = frame.size
    grain = graphite.crop((int(width*.39), int(height*.19), int(width*.62), int(height*.32)))
    backing = Image.new("L", frame.size)
    for row, top in enumerate(range(0, height, grain.height)):
        tile = ImageOps.flip(grain) if row % 2 else grain
        for col, left in enumerate(range(0, width, grain.width)):
            backing.paste(ImageOps.mirror(tile) if col % 2 else tile, (left, top))

    # The shared empty-slot artwork has a large minus sign; retain its genuine outer rim.
    y, x = np.ogrid[:height, :width]
    radius = np.hypot((x-width*.498)/width, (y-height*.482)/height)
    fade = Image.fromarray((np.clip((.303-radius)/.035, 0, 1)*255).astype("uint8"))
    plate = Image.composite(backing, ImageOps.grayscale(frame), fade).convert("RGBA")
    plate.putalpha(frame.getchannel("A"))
    part = Image.open(subject).convert("RGBA")
    part = part.crop(part.getchannel("A").getbbox())
    alpha = part.getchannel("A")
    part = ImageOps.grayscale(part).convert("RGBA")
    part.putalpha(alpha)
    left = (width-part.width)//2
    top = round(height*.484-part.height*.5)
    shadow_mask = Image.new("L", frame.size)
    shadow_mask.paste(alpha, (left+3, top+height//85))
    shadow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    shadow.putalpha(shadow_mask.filter(ImageFilter.GaussianBlur(width/120)).point(lambda v: round(v*.71)))
    plate.alpha_composite(shadow)
    plate.alpha_composite(part, (left, top))
    plate.resize((1024, 1024), Image.Resampling.LANCZOS).save(HERE / "Exports/muzzle_sniper_zhiming.png")


if __name__ == "__main__":
    compose(sys.argv[1])
