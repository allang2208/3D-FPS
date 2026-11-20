"""Dye the R4 workwear and paint flour onto the cut apron and folded cloth."""
from pathlib import Path
import json
import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/VillageBaker/WardrobeR1/Textures'
DONOR = ROOT / 'SourceAssets/VillageCarpenterNPC/Outfit/Textures'


def save(slot, kind, arr):
    Image.fromarray(np.uint8(np.clip(np.round(arr), 0, 255))).save(
        OUT / f'T_Baker_{slot}_{kind}.png', compress_level=4)


def tile(slot, kind, x, y):
    with Image.open(DONOR / f'T_Carpenter_{slot}_{kind}.png') as im:
        source = np.asarray(im.convert('RGB'))
    return cv2.remap(source, (x % 1 * source.shape[1]).astype('f'),
                     (y % 1 * source.shape[0]).astype('f'),
                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)


def noise(rng, u, v, width, height):
    field = rng.standard_normal((height, width)).astype('f')
    return cv2.remap(field, (u * width).astype('f'), (v * height).astype('f'),
                     cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)


def painted_cloth(name, seed):
    apron = name == 'Apron'
    h, w = (2048, 3072) if apron else (1536, 1024)
    v, u = np.mgrid[0:h, 0:w].astype(np.float32)
    u /= w
    v /= h
    rng = np.random.default_rng(seed)
    carrier = 'Canvas' if apron else 'Linen'
    if apron:
        # The sheet is hemmed at the bottom and banded across its full physical width.
        sx, sy = 3.9, 2.9
        shade, red = (159, 133, 107), (132, 79, 65)
        wobble = .0007 * noise(rng, u, v, 34, 10)
        stripes = ((abs(v + wobble - .835) < .014) | (abs(v + wobble - .889) < .012))
        blot = (1.05 * np.exp(-((u - .445) / .102) ** 2 - ((v - .188) / .106) ** 2)
                + .60 * np.exp(-((u - .59) / .08) ** 2 - ((v - .148) / .092) ** 2)
                + .39 * np.exp(-((u - .41) / .13) ** 2 - ((v - .41) / .23) ** 2))
    else:
        sx, sy = .87, 1.65
        shade, red = (201, 177, 149), (141, 84, 68)
        warp = u + .0015 * noise(rng, u, v, 18, 9)
        weft = v + .001 * noise(rng, u, v, 21, 12)
        stripes = ((abs(warp - .15) < .012) | (abs(warp - .195) < .022)
                   | (abs(warp - .249) < .009) | (abs(warp - .86) < .012)
                   | (abs(weft - .874) < .010) | (abs(weft - .906) < .006)
                   | (abs(weft - .935) < .013))
        blot = .26 * np.exp(-((u - .53) / .32) ** 2 - ((v - .63) / .26) ** 2)
    grain = tile(carrier, 'BC', u * sx, v * sy).astype('f')
    light = grain.mean(2) / grain.mean() - 1
    cloud = noise(rng, u, v, 14, 18)
    fine = noise(rng, u, v, 279, 217)
    dots = rng.random((h, w), dtype=np.float32)
    pigment = np.array(shade) + stripes[:, :, None] * (np.array(red) - np.array(shade))
    pigment = pigment * (1. + .93 * light + .031 * cloud)[:, :, None]
    dust = np.clip(blot * (.52 + .40 * cloud + .28 * fine + .22 * dots)
                   + .12 * np.maximum(0, fine - .9) * (dots > .74), 0, .84)
    dust += (1 - dust) * .37 * (dots > .975) * np.clip(.38 + blot * 1.1, 0, 1)
    save(name, 'BC', pigment * (1 - dust[:, :, None]) + np.array([229, 217, 196]) * dust[:, :, None])
    normal = tile(carrier, 'N', u * sx, v * sy)
    normal[:, :, 1] = 255 - normal[:, :, 1]
    save(name, 'N', normal)
    orm = tile(carrier, 'ORM', u * sx, v * sy)
    orm[:, :, 1] = np.clip(orm[:, :, 1] + 13. * dust, 0, 255)
    save(name, 'ORM', orm)


def dye_tile(slot, donor, pigment):
    for kind in ('BC', 'N', 'ORM'):
        with Image.open(DONOR / f'T_Carpenter_{donor}_{kind}.png') as im:
            data = np.asarray(im.convert('RGB')).copy()
        if kind == 'BC':
            # Keep the wear and strand relief while replacing the carpenter's dye.
            avg = data.reshape(-1, 3).mean(0)
            value = data / np.maximum(avg, 1.)
            data = np.asarray(pigment) * (1 + 1.12 * (value - 1))
        if kind == 'N':
            data[:, :, 1] = 255 - data[:, :, 1]
        save(slot, kind, data)


def skin_roughness(garment, packed):
    # The native SRMF green channel already contains normalized roughness. Adding
    # half the entire range clipped almost every visible forearm and neck texel.
    with Image.open(packed) as im:
        native = np.asarray(im.getchannel('G').resize((2048, 2048), Image.Resampling.LANCZOS)).astype('f')
    floor, span = (.55, .38) if garment == 'Skin' else (.63, .34)
    rough = floor * 255 + span * native
    save(garment, 'ORM', np.stack((np.full_like(rough, 255), rough, np.zeros_like(rough)), axis=2))


def skin_maps():
    native = ROOT / 'SourceAssets/JasonStrong20261117'
    textures = native / 'R2_LongLegs/textures'
    with (native / 'R3_ArmsRefined/AnatomyReview/derived_saved_mesh.json').open() as file:
        body = json.load(file)
    native_uv = np.asarray(body['triangle_uvs'])
    centers = np.asarray(body['positions'])[np.asarray(body['triangles'])].mean(axis=1)
    material = np.asarray(body['triangle_materials'])
    size = 2048
    arms = np.flatnonzero((material == 1) | (material == 2))
    mask = np.zeros((size, size), dtype=np.float32)
    for index in arms:
        x, y, z = centers[index]
        forearm = np.exp(-((abs(x) - 40.7) / 4.0) ** 2 - ((z - 113.7) / 8.2) ** 2)
        hand = np.exp(-((abs(x) - 46.5) / 5.2) ** 2 - ((y - 16.2) / 7.8) ** 2)
        alpha = .49 * hand + .27 * forearm
        cv2.fillConvexPoly(mask, np.rint(native_uv[index] * (size - 1)).astype(np.int32), float(alpha))
    mask = cv2.GaussianBlur(mask, (0, 0), 3.5)
    rng = np.random.default_rng(7139)
    v, u = np.mgrid[:size, :size].astype('f') / size
    dust = mask * np.clip(.48 + .29 * noise(rng, u, v, 79, 93) + .31 * noise(rng, u, v, 269, 296), 0, 1.)
    for garment, source, normal, packed in (
            ('Skin', 'T_Jason_body.png', 'T_Body_N.png', 'T_Body_SRMF.png'),
            ('NativeNeck', 'T_Jason_head.png', 'T_Head_LOD2_N.png', 'T_Head_SRMF.png')):
        with Image.open(textures / source) as im:
            color = np.asarray(im.convert('RGB')).astype('f') * [0.87, .81, .77]
        if garment == 'Skin':
            color = color * (1. - dust[:, :, None]) + dust[:, :, None] * [217, 202, 181]
        save(garment, 'BC', color)
        with Image.open(textures / normal) as im:
            n = np.asarray(im.convert('RGB').resize((size, size), Image.Resampling.LANCZOS)).copy()
        n[:, :, 1] = 255 - n[:, :, 1]
        save(garment, 'N', n)
        skin_roughness(garment, textures / packed)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    swatches = {
        'Shirt': ('Linen', (77, 76, 84)),
        'Cuff': ('Linen', (105, 101, 103)),
        'Pants': ('Twill', (77, 60, 49)),
        'Boot': ('Boot', (73, 53, 41)),
        'Sole': ('Sole', (47, 36, 30)),
        'Sash': ('Canvas', (164, 140, 111)),
        'Thread': ('Thread', (128, 109, 93)),
        'Button': ('Saddle', (111, 78, 45)),
    }
    for slot, (donor, pigment) in swatches.items():
        dye_tile(slot, donor, pigment)
    painted_cloth('Apron', 1329)
    painted_cloth('Towel', 6093)
    skin_maps()


if __name__ == '__main__':
    main()
