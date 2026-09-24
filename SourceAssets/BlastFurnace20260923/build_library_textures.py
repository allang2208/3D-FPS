"""Build the furnace's PBR sets from the project's own UnrealNormandy library.

    python SourceAssets/BlastFurnace20260923/build_library_textures.py

Replaces the procedural maps with the pack's 4096 photogrammetry sets. The
packing convention was read off the data rather than guessed:

* ``BaseColor`` / ``Albedo`` -> BaseColor (sRGB)
* ``Normal``                 -> Normal
* ``RHAOM``.R                -> Roughness
* ``RHAOM``.B                -> Ambient Occlusion
* ``RHAOM``.G                -> Height (unused here; the meshes are geometric)
* ``RHAOM``.A                -> Metallic, where the export kept the alpha

The output filenames are the ones ``author_blast_furnace.py`` and
``install/revise_blast_furnace.py`` already expect, so neither the Blender
preview nor the UE material graphs need to change.

Source pack: Sharur's Normandy Village + PCG Plants (Fab). The pack's own
assets are never modified; the export and the derived maps live under Saved/
and this folder.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

SRC = Path('D:/FPS3D/FPSGAME/Saved/BlastFurnace20260923/NormandyPNG')
SMALL = Path('D:/FPS3D/FPSGAME/Saved/BlastFurnace20260923/NormandySmall')
OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlastFurnace20260923/Authored/Textures')
OUT.mkdir(parents=True, exist_ok=True)

# slot -> (basecolour family, basecolour suffix, normal family, rhaom family, size, notes)
LIBRARY = {
    # The pack has no tileable brick. T_HB_Wall4x4_00A is a photogrammetry
    # atlas for the ruined-wall meshes: part of it is a brick wall, the rest is
    # stretched gutter smear, and even inside the brick block the apparent
    # brick size varies with the scan's perspective. A block clear of the smear
    # is cut out and mapped once around the shaft, so nothing tiles; the block
    # is validated against the atlas's AO channel before it is accepted.
    'BlastFurnace_Firebrick': dict(
        base='T_HB_Wall4x4_00A', base_suffix='BaseColor', normal='T_HB_Wall4x4_00A',
        rhaom='T_HB_Wall4x4_00A', crop=(60, 2400, 3460, 4090),
        validate_ao=True, metallic=None),
    'BlastFurnace_Masonry': dict(
        base='T_StoneSurface_01A', base_suffix='BaseColor', normal='T_StoneSurface_01A',
        rhaom='T_StoneSurface_01A', metallic=None),
    'BlastFurnace_WroughtIron': dict(
        base='T_MetalRust_00A', base_suffix='BaseColor', normal='T_MetalRust_00A',
        rhaom='T_MetalRust_00A', metallic='rust'),
    'BlastFurnace_ClayLuting': dict(
        base='T_SoilSurface_02A', base_suffix='BaseColor', normal='T_SoilSurface_02A',
        rhaom='T_SoilSurface_02A', metallic=None),
    'BlastFurnace_SlagLining': dict(
        base='T_LC_BasaltCliff_00A', base_suffix='Albedo', normal='T_LC_BasaltCliff_00A',
        rhaom='T_LC_BasaltCliff_00A', metallic=None, exposure=0.72),
    'BlastFurnace_EmberBed': dict(
        base='T_LC_BasaltCliffCracked_00A', base_suffix='Albedo',
        normal='T_LC_BasaltCliffCracked_00A', rhaom='T_LC_BasaltCliffCracked_00A',
 metallic=None, exposure=0.55),
    'BlastFurnace_OreLump': dict(
        base='T_LC_RockBasaltLichen_00A', base_suffix='Albedo',
        normal='T_LC_RockBasaltLichen_00A', rhaom='T_LC_RockBasaltLichen_00A',
 metallic=None),
}

report = {}


def load(family, suffix, crop=None, half=True):
    path = SRC / ('%s_%s.png' % (family, suffix))
    if not path.exists():
        raise RuntimeError('Missing exported library map: ' + str(path))
    with Image.open(path) as image:
        image = image.convert('RGBA' if 'A' in image.getbands() else 'RGB')
        if crop:
            image = image.crop(crop)
        # np.array copies. np.asarray here returns a view onto the decoder's
        # buffer, which is freed when the with-block closes.
        data = np.array(image, dtype=np.float32) / 255.0
    return downscale2(data) if half else data


def clean_rectangle(mask):
    """Largest all-true axis-aligned rectangle in a boolean mask.

    Standard largest-rectangle-in-histogram sweep, run on a downsampled mask so
    a 4096 map costs nothing.
    """
    height, width = mask.shape
    heights = np.zeros(width, np.int32)
    best = (0, 0, 0, 0, 0)  # area, x0, y0, x1, y1
    for y in range(height):
        heights = np.where(mask[y], heights + 1, 0)
        stack = []
        for x in range(width + 1):
            current = heights[x] if x < width else 0
            start = x
            while stack and stack[-1][1] >= current:
                index, bar = stack.pop()
                area = bar * (x - index)
                if area > best[0]:
                    best = (area, index, y - bar + 1, x, y + 1)
                start = index
            stack.append((start, current))
    return best


def erode(mask, passes=1):
    """3x3 minimum filter, enough to drop isolated speckle from a mask."""
    out = mask
    for _ in range(passes):
        source = out
        out = source.copy()
        out[1:, :] &= source[:-1, :]
        out[:-1, :] &= source[1:, :]
        out[:, 1:] &= source[:, :-1]
        out[:, :-1] &= source[:, 1:]
    return out


def dilate(mask, passes=1):
    """3x3 maximum filter; paired with erode it closes mortar-joint holes so the
    strict all-true rectangle search can still find a large block."""
    out = mask
    for _ in range(passes):
        source = out
        out = source.copy()
        out[1:, :] |= source[:-1, :]
        out[:-1, :] |= source[1:, :]
        out[:, 1:] |= source[:, :-1]
        out[:, :-1] |= source[:, 1:]
    return out


BRICK_COURSE_CM = 8.0


def course_period(profile):
    """Dominant vertical period of a brick wall, in pixels, by autocorrelation."""
    signal = profile - profile.mean()
    correlation = np.correlate(signal, signal, mode='full')[len(signal) - 1:]
    correlation /= correlation[0] if correlation[0] else 1.0
    low, high = 40, min(len(correlation) - 1, 260)
    if high <= low:
        return None
    best = low + int(np.argmax(correlation[low:high]))
    return best if correlation[best] > 0.15 else None


def auto_brick_crop():
    """Find the clean brick block in the wall atlas and align it to whole courses.

    The atlas bakes no ambient occlusion into its gutter smear, so the AO
    channel separates real brick (bright) from the smear (near black) -- colour
    channels do not, because the smear carries reddish streaks too. Closing
    fills the mortar joints, which are a couple of samples wide at this step.

    The block is then trimmed to a whole number of brick courses and reported
    with a physical size, so the shaft can tile it vertically without a visible
    seam and with the texture courses matching the modelled course height.
    """
    step = 8
    ao = load('T_HB_Wall4x4_00A', 'RHAOM', half=False)[..., 2]
    base = load('T_HB_Wall4x4_00A', 'BaseColor', half=False)
    redness = base[..., 0] - base[..., 2]
    mask = erode((ao[::step, ::step] > 0.35) & (redness[::step, ::step] > 0.04), passes=1)
    mask = erode(dilate(mask, passes=3), passes=3)
    area, x0, y0, x1, y1 = clean_rectangle(mask)
    box = [int(x0) * step, int(y0) * step, int(x1) * step, int(y1) * step]
    check = float(ao[box[1]:box[3], box[0]:box[2]].mean())
    if int(area * step * step) < 2000000 or check < 0.6:
        raise RuntimeError('Brick auto-crop is too small or landed on the atlas smear: '
                           'box=%s ao=%.3f' % (box, check))

    # Align the bottom edge up to a whole number of courses.
    region = base[box[1]:box[3], box[0]:box[2]]
    profile = region.mean(axis=(1, 2))
    period = course_period(profile)
    info = {'sampled_px': int(area * step * step), 'crop_ao_mean': round(check, 3),
            'raw_size_px': [box[2] - box[0], box[3] - box[1]]}
    if period:
        courses = max(3, int((box[3] - box[1]) // period))
        box[3] = box[1] + int(round(courses * period))
        info.update(course_period_px=period, courses=courses,
                    physical_tile_cm=[round((box[2] - box[0]) * BRICK_COURSE_CM / period, 2),
                                      round(courses * BRICK_COURSE_CM, 2)])
    else:
        info['course_period_px'] = None
    info['crop_size_px'] = [box[2] - box[0], box[3] - box[1]]
    return tuple(box), info


def downscale2(array):
    """Exact 2x2 box downscale.

    PIL's resize and thumbnail return an all-zero image for these file-backed
    4096 maps in this build (verified with a synthetic image, which resizes
    fine), so the reduction is done in numpy. For a pure halving a box filter
    is also the better filter.
    """
    height, width = array.shape[:2]
    height -= height % 2
    width -= width % 2
    view = array[:height, :width]
    if view.ndim == 3:
        return view.reshape(height // 2, 2, width // 2, 2, view.shape[2]).mean(axis=(1, 3))
    return view.reshape(height // 2, 2, width // 2, 2).mean(axis=(1, 3))


def to_srgb(linear):
    linear = np.clip(linear, 0.0, 1.0)
    return np.where(linear <= 0.0031308, linear * 12.92,
                    1.055 * np.power(np.maximum(linear, 1e-8), 1.0 / 2.4) - 0.055)


def save(name, array):
    data = np.uint8(np.clip(array, 0, 1) * 255)
    path = OUT / name
    Image.fromarray(data).save(path)
    return path


for slot, spec in LIBRARY.items():
    crop = spec.get('crop')
    crop_info = None
    if spec.get('validate_ao'):
        # The atlas's gutter smear bakes no ambient occlusion and reads near
        # black, so a mean AO check proves the crop missed it. A hand-guessed
        # crop that cut into the smear put a green band on top of the shaft.
        probe = load(spec['rhaom'], 'RHAOM', crop, half=False)[..., 2]
        ao_mean = float(probe.mean())
        if ao_mean < 0.6:
            raise RuntimeError('%s: crop AO mean %.3f looks like atlas smear' % (slot, ao_mean))
        crop_info = {'crop_ao_mean': round(ao_mean, 3)}
    base = load(spec['base'], spec['base_suffix'], crop)
    normal = load(spec['normal'], 'Normal', crop)
    rhaom = load(spec['rhaom'], 'RHAOM', crop)

    # Library BaseColor/Albedo is sRGB-encoded; expose everything to the
    # pipeline in linear so the furnace materials stay consistent.
    base_lin = np.where(base[..., :3] <= 0.04045, base[..., :3] / 12.92,
                        np.power((base[..., :3] + 0.055) / 1.055, 2.4))
    note = []
    if spec.get('exposure'):
        base_lin = base_lin * spec['exposure']
        note.append('exposure %.2f' % spec['exposure'])

    metallic = np.zeros(base_lin.shape[:2], np.float32)
    if spec.get('metallic') == 'rust':
        # T_MetalRust_00A is a heavily orange-rusted sheet. The project already
        # desaturates and darkens it for the production tools; the same
        # treatment is applied here so the bands read as iron, not as rust.
        luma = base_lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        base_lin = base_lin * 0.38 + luma[..., None] * 0.62
        base_lin = np.clip(base_lin * 0.72, 0.0, 1.0)
        note.append('desaturated 0.62 and darkened 0.72 like the tool materials')
        if rhaom.ndim == 3 and rhaom.shape[2] == 4:
            metallic = rhaom[..., 3]
            note.append('metallic from RHAOM alpha')
        else:
            # No alpha survived the export: treat the rusted (rough) areas as
            # dielectric and the smoother metal as conductive.
            rough = rhaom[..., 0]
            metallic = np.clip((1.0 - np.clip((rough - 0.45) / 0.35, 0.0, 1.0)) * 0.9, 0.0, 1.0)
            note.append('metallic derived from roughness (no alpha in the export)')

    save('%s_BaseColor.png' % slot, to_srgb(base_lin))
    save('%s_Normal.png' % slot, normal[..., :3])
    save('%s_Roughness.png' % slot, rhaom[..., 0])
    save('%s_AO.png' % slot, rhaom[..., 2])
    save('%s_Metallic.png' % slot, metallic)
    if rhaom.ndim == 3 and rhaom.shape[2] == 4:
        save('%s_Height.png' % slot, rhaom[..., 1])

    report[slot] = {
        'source_base': '%s_%s' % (spec['base'], spec['base_suffix']),
        'source_normal': '%s_Normal' % spec['normal'],
        'source_rhaom': '%s_RHAOM' % spec['rhaom'],
        'crop': spec.get('crop'), 'output_size': [base.shape[1], base.shape[0]],
        'base_linear_mean': [round(float(v), 4) for v in base_lin.reshape(-1, 3).mean(0)],
        'metallic_mean': round(float(metallic.mean()), 4),
        'notes': note}
    print('LIBRARY_MATERIAL %-28s %s' % (slot, report[slot]['base_linear_mean']), flush=True)

(OUT.parent / 'library-textures.json').write_text(
    json.dumps({'source_pack': "Sharur's Normandy Village + PCG Plants (Fab)",
                'packing': {'RHAOM.R': 'roughness', 'RHAOM.G': 'height',
                            'RHAOM.B': 'ambient occlusion', 'RHAOM.A': 'metallic'},
                'materials': report, 'runtime_tested': False}, ensure_ascii=False, indent=2),
    encoding='utf-8')
print('LIBRARY_TEXTURES_BUILT', len(report))
