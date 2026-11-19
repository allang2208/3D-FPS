"""Author tileable carpenter workwear and the folding rule / pencil UV atlas.

RGB maps are sRGB. Tangent normals are DirectX, with Y down the image.
The three linear mask channels are occlusion, roughness and metallic.
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'SourceAssets/VillageBlacksmithNPC20261118/FinishR2/BodyOutfit/Textures'
OUT = ROOT / 'SourceAssets/VillageCarpenterNPC/Outfit/Textures'
TAU = 2.0 * np.pi


def save(slot, kind, values):
    target = OUT / f'T_Carpenter_{slot}_{kind}.png'
    staging = target.with_suffix('.tmp')
    pixels = np.clip(np.rint(values), 0, 255).astype(np.uint8)
    Image.fromarray(pixels).save(staging, format='PNG', compress_level=5)
    staging.replace(target)


def smooth(a, b, values):
    t = np.clip((values - a) / (b - a), 0., 1.)
    return t * t * (3. - 2. * t)


class Swatch:
    """All procedural coordinates wrap on a square tile, including brush marks."""

    def __init__(self, size, seed):
        self.size = size
        self.rng = np.random.default_rng(seed)
        y, x = np.mgrid[:size, :size].astype(np.float32)
        self.x = x / size
        self.y = y / size

    def noise(self, across, down=None):
        down = across if down is None else down
        grid = self.rng.standard_normal((down, across), dtype=np.float32)
        return cv2.remap(grid, self.x * across, self.y * down, cv2.INTER_CUBIC,
                         borderMode=cv2.BORDER_WRAP)

    def small_marks(self, count, length, thickness, angle, angle_spread, bend=.1):
        """Broken fibres, minute tool marks or pores with independently varied lengths."""
        rng = self.rng
        tile = np.zeros((self.size, self.size), dtype=np.float32)
        phase = np.linspace(-.5, .5, 7)
        for _ in range(count):
            start = rng.uniform(0., self.size, 2)
            tangent = angle + rng.normal(0., angle_spread)
            along = np.array([np.cos(tangent), np.sin(tangent)])
            across = np.array([-along[1], along[0]])
            run = length * rng.uniform(.42, 1.65)
            arc = rng.uniform(-bend, bend) * run * (1. - 4. * phase ** 2)
            points = start + np.outer(phase * run, along) + np.outer(arc, across)
            strength = rng.uniform(.3, 1.)
            width = max(1, round(thickness * rng.uniform(.72, 1.4)))
            # cv2's fixed-point line positions preserve thinner marks at arbitrary angles.
            for off_y in _copies(points[:, 1], self.size, width):
                for off_x in _copies(points[:, 0], self.size, width):
                    fixed = np.rint((points + [off_x, off_y]) * 16.).astype(np.int32)
                    cv2.polylines(tile, [fixed], False, strength, width, shift=4)
        return gaussian_filter(tile, .72, mode='wrap')


def _copies(values, size, margin):
    offsets = [0]
    if values.min() < margin:
        offsets.append(size)
    if values.max() >= size - margin:
        offsets.append(-size)
    return offsets


def captured_grain(slot, size):
    # Use the original authored textile / hide capture for the irregular surface
    # grain. Isolate its relief from the donor's pigment and broad baked contrast.
    with Image.open(SOURCE / f'T_Smith_{slot}_BC.png') as image:
        gray = image.convert('L').resize((size, size), Image.Resampling.LANCZOS)
    value = np.log(np.asarray(gray, np.float32) + 10.)
    band = value - gaussian_filter(value, size / 125., mode='wrap')
    return np.clip(band / max(band.std(), .015), -2.8, 2.8)


def normal_map(height):
    height = gaussian_filter(height, .50, mode='wrap')
    dx = .5 * (np.roll(height, -1, 1) - np.roll(height, 1, 1))
    dy = .5 * (np.roll(height, -1, 0) - np.roll(height, 1, 0))
    inv = 1. / np.sqrt(1. + dx * dx + dy * dy)
    return 127.5 * (1. + np.stack((-dx * inv, -dy * inv, inv), axis=2))


def maps(slot, color, height, ao, rough, metallic=0.):
    masks = np.stack(np.broadcast_arrays(ao, rough, metallic), axis=-1)
    save(slot, 'BC', color)
    save(slot, 'N', normal_map(height))
    save(slot, 'ORM', np.clip(masks, 0., 1.) * 255.)
    print(f'Saved {slot} BC/N/ORM at {color.shape[0]} px.', flush=True)


def dye(base, brightness, warmth, shift):
    return np.asarray(base, np.float32) * brightness[..., None] + warmth[..., None] * np.asarray(shift, np.float32)


def over(slot, i, j):
    if slot == 'Twill':
        # Three warp floats and one weft pick. Moving the binding point one end
        # every row produces the diagonal wale without painting a stripe.
        return ((i - j) % 4 != 0).astype(np.float32)
    if slot == 'Canvas':
        # Two ends travel through each shed together on this heavier duck.
        return ((i // 2 + j) % 2 == 0).astype(np.float32)
    return ((i + j) % 2 == 0).astype(np.float32)


def cloth(slot, size, counts, pigment, roughness, seed):
    tile = Swatch(size, seed)
    nx, ny = counts
    bath = tile.noise(6)
    mid = tile.noise(27)
    warp_slub = tile.noise(nx, 14)
    weft_slub = tile.noise(19, ny)
    irregularity = {'Linen': .15, 'Canvas': .065, 'Twill': .045}[slot]
    # Fibre thickness varies slowly along each continuous strand. The yarns
    # also bow gradually across several neighbours, especially in woven flax.
    u = tile.x * nx + .23 * tile.noise(8, 10) + irregularity * tile.noise(40, 19)
    v = tile.y * ny + .19 * tile.noise(11, 8) + irregularity * tile.noise(19, 44)
    i = np.floor(u + .5).astype(np.int32)
    j = np.floor(v + .5).astype(np.int32)
    floor_u = np.floor(u).astype(np.int32)
    floor_v = np.floor(v).astype(np.int32)
    mix_u = smooth(0., 1., (u - floor_u).astype(np.float32))
    mix_v = smooth(0., 1., (v - floor_v).astype(np.float32))
    warp_over = (1. - mix_v) * over(slot, i, floor_v) + mix_v * over(slot, i, floor_v + 1)
    weft_over = 1. - ((1. - mix_u) * over(slot, floor_u, j) + mix_u * over(slot, floor_u + 1, j))
    du = (u - i).astype(np.float32)
    dv = (v - j).astype(np.float32)
    warp_width = np.clip(1. + irregularity * warp_slub, .72, 1.17)
    weft_width = np.clip(1. + irregularity * weft_slub, .74, 1.16)
    warp = np.sin(np.maximum(.5 - np.abs(du) / warp_width, 0.) * np.pi) ** .75 * (.41 + .59 * warp_over)
    weft = np.sin(np.maximum(.5 - np.abs(dv) / weft_width, 0.) * np.pi) ** .75 * (.41 + .59 * weft_over)
    # At intersections only the top yarn is exposed.
    top = np.maximum(warp, weft)
    face = smooth(-.12, .12, warp - weft)
    yarn = face * warp_slub + (1. - face) * weft_slub
    relief = top - top.mean()
    donor = 'Twill' if slot == 'Twill' else 'Linen'
    fibre = captured_grain(donor, size)
    nap = tile.small_marks(round(size * .46), size * .0048, 1., -.35, .85)
    dry_fibres = np.clip(yarn * .37 + .21 * mid + .17 * fibre - .26, 0., 1.)
    if slot == 'Twill':
        warmth = .42 * (1. - face) + dry_fibres
        shift = (13., 12., 8.)
    elif slot == 'Linen':
        warmth = dry_fibres + .22 * yarn
        shift = (9., 6.5, 2.)
    else:
        warmth = dry_fibres + .16 * face
        shift = (14., 11., 6.)
    brightness = 1. + .095 * relief + .031 * bath + .013 * mid + .015 * yarn + .017 * fibre + .035 * nap
    heights = {'Linen': 2.35, 'Twill': 1.22, 'Canvas': 2.85}
    height = heights[slot] * top + .24 * fibre + .25 * nap + .11 * yarn
    ao = .979 - .082 * smooth(.47, .08, top)
    rough = roughness + .025 * bath + .012 * mid + .025 * dry_fibres - .046 * relief + .009 * fibre
    maps(slot, dye(pigment, brightness, warmth, shift), height, ao, rough)


def hide(slot, seed):
    # The flatter, waxed bridle hide and the softer boot upper retain different
    # pore spacing, creasing, gloss and dye even before the garment wear pass.
    belt = slot == 'Saddle'
    tile = Swatch(1024, seed)
    grain = captured_grain(slot, tile.size)
    cloud = tile.noise(5)
    mottling = tile.noise(18, 24)
    pore = smooth(.67, 2.1, tile.noise(263, 213) if belt else tile.noise(193, 177))
    flex = tile.noise(10, 38) + .37 * tile.noise(27, 69)
    folds = np.exp(-(flex / (.105 if belt else .18)) ** 2) * smooth(-1., 1.1, mottling)
    skive = tile.small_marks(155 if belt else 210, 17 if belt else 12, 1.0, -.45, .54)
    wax = smooth(-.7, 1.45, .74 * cloud + .34 * mottling + .18 * grain)
    pigment = (69, 45, 31) if belt else (55, 40, 33)
    detail = .045 * grain - .05 * pore - .046 * folds + .038 * mottling + .035 * cloud
    color = dye(pigment, 1. + detail - .06 * wax, .45 * wax + skive, (15., 8.5, 4.))
    height = (.44 if belt else .67) * grain - .72 * pore - (.53 if belt else .91) * folds - .39 * skive
    ao = .988 - .047 * pore - .031 * folds
    rough = (.53 if belt else .64) - .135 * wax + .032 * mottling + .048 * pore + .079 * skive
    maps(slot, color, height, ao, rough)


def sole():
    tile = Swatch(512, 84249)
    rubber = tile.noise(127)
    crumb = tile.noise(62, 70)
    press = tile.noise(13)
    fleck = smooth(.92, 1.96, crumb)
    drag = tile.small_marks(425, 7., 1.25, -.86, .62)
    color = dye((44, 38, 34), 1. + .037 * press + .031 * rubber, .42 * fleck + drag, (12., 10., 7.))
    maps('Sole', color, .49 * rubber + .34 * crumb - .43 * drag,
         .986 - .031 * smooth(-.4, -1.66, rubber), .83 + .034 * press - .051 * drag + .021 * fleck)


def brass():
    tile = Swatch(512, 28233)
    cast = tile.noise(64, 51)
    coarse = tile.noise(8)
    abrasion = tile.small_marks(630, 17, .8, -.12, .32, .035)
    pit = smooth(1.18, 2.15, tile.noise(145))
    oxide = smooth(.13, 1.69, .86 * coarse + .46 * tile.noise(25) + .18 * cast)
    # Tarnish attenuates the copper-alloy reflectance. Settled, dark oxide in
    # casting pits is dielectric. Scratches break most clearly in roughness.
    bright = (1. + .024 * cast + .018 * coarse)[..., None] * np.array([210., 170., 106.], np.float32)
    oxide_color = np.array([86., 75., 49.], np.float32)
    tarnish = oxide[..., None] * .78
    color = bright * (1. - tarnish) + oxide_color * tarnish - 9. * pit[..., None]
    height = .21 * cast - .82 * pit - .51 * abrasion
    rough = .36 + .24 * oxide + .057 * pit + .091 * abrasion + .016 * cast
    metallic = .98 - .63 * oxide ** 2 - .10 * pit * oxide
    maps('Brass', color, height, .993 - .046 * pit, rough, metallic)


def thread():
    # A waxed cord is a twisted bundle, not a scaled-down piece of plain cloth.
    tile = Swatch(512, 92816)
    twist = .5 + .5 * np.cos(TAU * (64 * tile.x + 92 * tile.y + .12 * tile.noise(8)))
    nap = tile.small_marks(875, 5.5, 1., -.64, .38)
    wax = smooth(-.86, 1.29, tile.noise(22, 10))
    fibre = tile.noise(113, 121)
    color = dye((154, 126, 91), 1. + .078 * (twist - .5) + .018 * fibre,
                .65 * nap + .17 * wax, (15., 11., 6.))
    maps('Thread', color, .59 * twist + .15 * fibre + .24 * nap,
         .986 - .026 * (1. - twist), .797 - .071 * wax + .044 * nap)


def tool_atlas():
    size = 512
    tile = Swatch(size, 45773)
    u, v = tile.x, tile.y
    ripple = tile.noise(4, 7)
    vessels = tile.noise(121, 12)
    wood = np.sin(TAU * (u * 32. + .30 * np.sin(TAU * v) + .17 * ripple))
    rays = tile.small_marks(780, 4.8, 1., 1.53, .14)
    seal = tile.noise(15, 12)
    stroke = tile.small_marks(300, 9., .9, 1.44, .22)
    beech = dye((178, 142, 91), 1. + .043 * wood + .028 * vessels + .017 * seal,
                rays, (14., 9., 5.))
    # The hard edges of the pencil lose their oxblood enamel first. UV ranges
    # match the four islands in the carpentry tool geometry.
    edge_distance = np.minimum(np.abs(u - .56), np.abs(u - .73))
    chip = np.exp(-(edge_distance / .0065) ** 2) * smooth(-.13, 1.25, seal + .55 * vessels)
    paint = dye((128, 53, 37), 1. + .023 * seal + .018 * vessels, chip + .35 * stroke, (44., 49., 37.))
    cedar = dye((185, 134, 92), 1. + .065 * vessels + .035 * wood, rays, (18., 12., 7.))
    lead = dye((53, 52, 53), 1. + .055 * tile.noise(102) + .028 * seal, stroke, (12., 12., 12.))

    plate = np.select([(u < x)[..., None] for x in (.50, .75, .90)], [beech, paint, cedar], lead)
    rough = np.select([u < .50, u < .75, u < .90],
                      [.53 + .022 * vessels + .036 * seal + .071 * rays,
                       .44 + .035 * seal + .22 * chip, .76 + .031 * vessels],
                      .40 + .039 * seal + .045 * stroke)
    image = Image.fromarray(np.clip(np.rint(plate), 0, 255).astype(np.uint8))
    ink = Image.new('L', (size, size))
    ink_drawing = ImageDraw.Draw(ink)
    font = ImageFont.truetype('C:/Windows/Fonts/georgia.ttf', 22)
    # A leaf measures 10.83 cm along its mapped length. Preserve the original
    # endpoints and stop-label direction so both leaves share a calibrated face.
    left, top, bottom = .03 * size, .08 * size, .93 * size
    for mm in range(109):
        yy = round(top + mm / 108.3 * (bottom - top))
        extent = 57 if mm % 10 == 0 else 37 if mm % 5 == 0 else 19
        ink_drawing.line((left + 4, yy, left + 4 + extent, yy), fill=255, width=2 if mm % 10 == 0 else 1)
        if mm % 10 == 0:
            ink_drawing.text((left + 72, yy), str(mm // 10), anchor='lm', fill=255, font=font)
    ink_alpha = np.asarray(ink, dtype=np.float32) / 255.
    ink_values = dye((64, 50, 34), 1. + .022 * seal, rays, (5., 4., 3.))
    image.paste(Image.fromarray(np.clip(ink_values, 0, 255).astype(np.uint8)), (0, 0), ink)
    rough += .063 * ink_alpha
    # A peened pivot is brass at the centre and dulled around the shallow recess.
    pivot_x = (u * size - 187.) / 11.
    pivot_y = (v * size - 64.) / 11.
    pivot_r = np.sqrt(pivot_x ** 2 + pivot_y ** 2)
    pivot = smooth(1.04, .95, pivot_r)
    lip = smooth(.92, .61, pivot_r)
    hardware = dye((121, 99, 61), 1. + .033 * seal, lip, (57., 47., 24.))
    albedo = np.asarray(image, np.float32) * (1. - pivot[..., None]) + hardware * pivot[..., None]
    rough = rough * (1. - pivot) + (.53 - .14 * lip) * pivot
    metal = .93 * pivot
    ao = .992 - .145 * pivot * (1. - lip)
    save('Tools', 'BC', albedo)
    save('Tools', 'ORM', 255. * np.stack((ao, rough, metal), axis=2))
    print('Saved Tools BC/ORM at 512 px.', flush=True)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    cloth('Linen', 2048, (212, 198), (143, 135, 115), .846, 5468)
    cloth('Twill', 1024, (164, 156), (63, 71, 72), .806, 37263)
    cloth('Canvas', 2048, (208, 150), (150, 109, 60), .863, 65921)
    hide('Saddle', 35972)
    hide('Boot', 83572)
    sole()
    brass()
    thread()
    tool_atlas()
