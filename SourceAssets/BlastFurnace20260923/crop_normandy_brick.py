"""Cut the clean brick block out of the Normandy wall atlas and check it.

    python SourceAssets/BlastFurnace20260923/crop_normandy_brick.py

``T_HB_Wall4x4_00A`` is a UV atlas for the pack's ruined-wall meshes: only part
of it is an actual brick wall, the rest is stretched gutter smear. Tiling the
whole atlas would wrap that smear around the furnace, so the clean block is cut
out at full 4096 resolution and reported with its physical reading.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SRC = Path('D:/FPS3D/FPSGAME/Saved/BlastFurnace20260923/NormandyPNG')
SMALL = Path('D:/FPS3D/FPSGAME/Saved/BlastFurnace20260923/NormandySmall')
OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlastFurnace20260923/Authored/Normandy')
OUT.mkdir(parents=True, exist_ok=True)

# Full-resolution crop inside the brick block, staying clear of the smear.
CROPS = {
    'brick_00A': ('T_HB_Wall4x4_00A_BaseColor.png', (60, 2010, 3460, 4090)),
}

FONT = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 20)

report = {}
for key, (source, box) in CROPS.items():
    with Image.open(SRC / source) as image:
        crop = image.convert('RGB').crop(box)
        crop.save(OUT / ('%s_BaseColor.png' % key))
        report[key] = {'source': source, 'box': box, 'size': list(crop.size)}
        preview = crop.copy()
        preview.thumbnail((900, 900), Image.Resampling.LANCZOS)

# Side-by-side: the raw atlas and the crop, so the choice is visible.
with Image.open(SRC / 'T_HB_Wall4x4_00A_BaseColor.png') as atlas:
    atlas_small = atlas.convert('RGB')
    atlas_small.thumbnail((560, 560), Image.Resampling.LANCZOS)
    cropped = Image.open(OUT / 'brick_00A_BaseColor.png')
    crop_small = cropped.copy()
    crop_small.thumbnail((560, 560), Image.Resampling.LANCZOS)

sheet = Image.new('RGB', (1140, 620), (32, 34, 38))
draw = ImageDraw.Draw(sheet)
sheet.paste(atlas_small, (10, 40))
sheet.paste(crop_small, (580, 40))
draw.text((10, 12), 'T_HB_Wall4x4_00A full atlas (note the smear at top right)', font=FONT,
          fill=(238, 238, 232))
draw.text((580, 12), 'clean brick crop', font=FONT, fill=(238, 238, 232))
sheet.save(SMALL / '_brick_crop.png')

# Per-channel statistics of RHAOM, so the packing is read off the data.
for family in ('T_HB_Wall4x4_00A', 'T_MetalRust_00A', 'T_LC_GroundSoilExcavated_00A',
               'T_StoneSurface_01A'):
    path = SRC / ('%s_RHAOM.png' % family)
    if not path.exists():
        continue
    with Image.open(path) as image:
        import numpy as np
        arr = np.asarray(image.convert('RGB'), dtype=np.float32) / 255.0
    report.setdefault('rhaom', {})[family] = {
        channel: {'mean': round(float(arr[..., index].mean()), 3),
                  'std': round(float(arr[..., index].std()), 3)}
        for index, channel in enumerate('RGB')}

print('BRICK_CROP ' + str({k: v for k, v in report.items() if k != 'rhaom'}))
for family, channels in report.get('rhaom', {}).items():
    print('RHAOM %-32s %s' % (family, channels))
