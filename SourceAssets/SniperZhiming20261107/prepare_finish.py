"""Generate the two-sided, text-free graphic for the existing round metal shell."""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps
from scipy.ndimage import distance_transform_edt, gaussian_filter


EXPORT = Path(__file__).resolve().parent / "Exports"
WIDTH, HEIGHT = 2048, 1024
SUPERSAMPLE = 2
GOLD = (170, 129, 67, 255)
BRONZE = (140, 103, 60, 255)
SATIN = (97, 104, 108, 255)
GRAPHITE = (42, 46, 49, 255)
VIOLET = (108, 72, 132, 255)


def ribbon_outline():
    """Outline a single tapered ribbon along a sequence of smooth wave crests."""
    start = (453, 254)
    segments = [
        ((529, 254), (549, 254), (582, 225)),
        ((630, 182), (643, 121), (706, 121)),
        ((793, 121), (787, 337), (870, 337)),
        ((920, 337), (938, 202), (998, 202)),
        ((1047, 202), (1058, 267), (1105, 267)),
        ((1143, 267), (1152, 253), (1202, 253)),
        ((1260, 253), (1367, 253), (1410, 253)),
    ]
    curve = [start]
    for control_a, control_b, end in segments:
        for step in range(1, 29):
            t = step / 28
            weights = ((1-t)**3, 3*(1-t)**2*t, 3*(1-t)*t*t, t**3)
            curve.append(tuple(sum(w*v for w, v in zip(weights, axis))
                               for axis in zip(start, control_a, control_b, end)))
        start = end
    left, right = [], []
    for index, (x, y) in enumerate(curve):
        before = curve[max(0, index-1)]
        after = curve[min(len(curve)-1, index+1)]
        dx, dy = after[0]-before[0], after[1]-before[1]
        t = (x-453)/(1410-453)
        half_width = 24 - 12*t*t*(3-2*t) + 2.8*math.exp(-((t-.27)/.13)**2)
        scale = half_width / math.hypot(dx, dy)
        # Bias the two end cuts to follow the slashes without flattening the crests.
        shear = .43*max(0, 1-min(x-453, 1410-x)/54)**2
        offset_x = -dy*scale - shear*dx*scale
        left.append((x+offset_x, y+dx*scale))
        right.append((x-offset_x, y-dx*scale))
    return left + right[::-1]


def side_graphic():
    face = Image.new("RGBA", (WIDTH*SUPERSAMPLE, HEIGHT//2*SUPERSAMPLE))
    brush = ImageDraw.Draw(face)

    def shape(points, color):
        brush.polygon([(round(x*SUPERSAMPLE), round(y*SUPERSAMPLE)) for x, y in points], fill=color)

    # Paired slashes lead into the waveform. Open space separates each group at icon size.
    for x, color in ((259, SATIN), (333, BRONZE)):
        shape([(x, 297), (x+56, 202), (x+111, 202), (x+55, 297)], color)
    shape(ribbon_outline(), GOLD)

    # A punched-out lozenge and a violet inset form the end mark.
    shape([(1453, 253), (1562, 178), (1671, 253), (1562, 328)], GOLD)
    shape([(1481, 253), (1562, 197), (1643, 253), (1562, 309)], (0, 0, 0, 0))
    shape([(1520, 253), (1562, 224), (1604, 253), (1562, 282)], VIOLET)
    return face.resize((WIDTH, HEIGHT//2), Image.Resampling.LANCZOS)


def make_surface_map(atlas):
    """Pack tangent-space normals in RGB and finish roughness in alpha."""
    pixels = np.asarray(atlas, dtype=np.int16)
    height = np.zeros((HEIGHT, WIDTH), np.float32)
    roughness = np.full_like(height, .49)
    for color, bevel_width, relief, satin in (
        (GOLD, 5, 1.6, .33), (BRONZE, 5, 1.5, .39), (SATIN, 4, 1.0, .45),
        (GRAPHITE, 6, 1.4, .54), (VIOLET, 40, 9., .22),
    ):
        mask = (np.max(np.abs(pixels[:, :, :3]-color[:3]), axis=2)<3) & (pixels[:, :, 3]>127)
        # Pad across the circumference so the relief joins on the reverse face.
        padded = np.pad(mask, ((64, 64), (0, 0)), mode="wrap")
        distance = distance_transform_edt(padded)[64:-64]
        profile = np.clip(distance / bevel_width, 0., 1.)
        if color != VIOLET:
            profile = 1.-(1.-profile)**2
        height[mask] = relief*profile[mask]
        roughness[mask] = satin - .065*(1.-profile[mask])

    # Parallel satin marks affect highlights without painting grain into the albedo.
    rng = np.random.default_rng(117)
    grain = gaussian_filter(rng.standard_normal(height.shape).astype(np.float32),
                            sigma=(1.05, 19.), mode="wrap")
    roughness += .017*grain/max(grain.std(), .0001)
    height = gaussian_filter(height, sigma=.85, mode="wrap")
    nx = (np.roll(height, 1, axis=1)-np.roll(height, -1, axis=1))*.5
    ny = (np.roll(height, -1, axis=0)-np.roll(height, 1, axis=0))*.5
    length = np.sqrt(nx*nx+ny*ny+1.)
    packed = np.stack((.5+.5*nx/length, .5+.5*ny/length, .5+.5/length, roughness), axis=2)
    Image.fromarray(np.rint(255*np.clip(packed, 0, 1)).astype(np.uint8)).save(
        EXPORT / "T_Zhiming_RoundFinish.png")


def make_artwork():
    EXPORT.mkdir(exist_ok=True)
    atlas = Image.new("RGBA", (WIDTH, HEIGHT))
    brush = ImageDraw.Draw(atlas)
    for x, width, color in ((107, 78, GRAPHITE), (183, 29, BRONZE),
                            (1762, 38, BRONZE), (1800, 101, GRAPHITE), (1901, 20, SATIN)):
        brush.rectangle((x, 0, x+width-1, HEIGHT-1), fill=color)
    face = side_graphic()
    atlas.alpha_composite(face, (0, 218))
    # The far side crosses the UV wrap. Mirror the artwork around the top of the shell.
    reverse = ImageOps.flip(face)
    atlas.alpha_composite(reverse, (0, -218))
    atlas.alpha_composite(reverse, (0, HEIGHT-218))
    atlas.save(EXPORT / "T_Zhiming_RoundArtwork.png")
    make_surface_map(atlas)


if __name__ == "__main__":
    make_artwork()
