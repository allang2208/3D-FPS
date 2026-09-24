"""Downscale the exported Normandy maps and build a labelled contact sheet.

    python SourceAssets/BlastFurnace20260923/prepare_normandy_preview.py

Also reports the per-channel statistics of a couple of RHAOM maps so the
packing convention (which channel is roughness / AO / height / metallic) is
established from the data rather than guessed.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC = Path('D:/FPS3D/FPSGAME/Saved/BlastFurnace20260923/NormandyPNG')
SMALL = Path('D:/FPS3D/FPSGAME/Saved/BlastFurnace20260923/NormandySmall')
SMALL.mkdir(parents=True, exist_ok=True)
FONT = Path('C:/Windows/Fonts/arialbd.ttf')

# Base-colour candidates, grouped the way the furnace would use them.
GROUPS = [
    ('砖 BRICK', ['T_HB_Wall4x4_00A_BaseColor', 'T_HB_Wall4x4_01A_BaseColor',
                  'T_Mortar_00A_BaseColor']),
    ('砌石 ASHLAR', ['T_StoneSurface_00A_BaseColor', 'T_StoneSurface_01A_BaseColor',
                     'T_StoneSurface_02A_BaseColor', 'T_StoneSurface_03A_BaseColor']),
    ('岩 CLIFF / BASALT', ['T_CliffSurface_02A_BaseColor', 'T_CliffSurface_03A_BaseColor',
                           'T_LC_BasaltCliff_00A_Albedo', 'T_LC_RockBasaltLichen_00A_Albedo']),
    ('土 SOIL', ['T_LC_GroundSoilExcavated_00A_Albedo', 'T_SoilSurface_02A_BaseColor',
                 'T_LC_MossyGravel_00A_Albedo']),
    ('金属 METAL', ['T_MetalRust_00A_BaseColor']),
]
SIZE = 300

report = {'downscaled': 0, 'rhaom_channels': {}}

for png in sorted(SRC.glob('*.png')):
    target = SMALL / png.name
    if target.exists() and target.stat().st_size > 0:
        continue
    with Image.open(png) as image:
        image = image.convert('RGB')
        image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        image.save(target)
    report['downscaled'] += 1

# --- RHAOM packing: look at the data instead of trusting the name --------
for family in ('T_HB_Wall4x4_00A', 'T_MetalRust_00A', 'T_LC_GroundSoilExcavated_00A'):
    for suffix in ('RHAOM',):
        path = SRC / ('%s_%s.png' % (family, suffix))
        if not path.exists():
            continue
        with Image.open(path) as image:
            arr = np.asarray(image.convert('RGB'), dtype=np.float32) / 255.0
        report['rhaom_channels']['%s_%s' % (family, suffix)] = {
            'R': {'mean': round(float(arr[..., 0].mean()), 3), 'std': round(float(arr[..., 0].std()), 3)},
            'G': {'mean': round(float(arr[..., 1].mean()), 3), 'std': round(float(arr[..., 1].std()), 3)},
            'B': {'mean': round(float(arr[..., 2].mean()), 3), 'std': round(float(arr[..., 2].std()), 3)},
        }
        # Save the three channels side by side so the packing is visible.
        strips = Image.new('RGB', (SIZE * 3, SIZE), (0, 0, 0))
        for index in range(3):
            channel = Image.fromarray((arr[..., index] * 255).astype('uint8')).convert('RGB')
            channel = channel.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
            colour = [(230, 90, 80), (110, 220, 120), (110, 160, 240)][index]
            tint = Image.new('RGB', (SIZE, SIZE), colour)
            strips.paste(Image.blend(channel, tint, 0.35), (index * SIZE, 0))
        strips.save(SMALL / ('_rhaom_%s.png' % family))

# --- contact sheet ------------------------------------------------------
font = ImageFont.truetype(str(FONT), 22)
small = ImageFont.truetype(str(FONT), 17)
rows = sum(1 + (len(items) + 3) // 4 for _title, items in GROUPS)
sheet = Image.new('RGB', (SIZE * 4 + 20, (SIZE + 34) * rows + 20), (32, 34, 38))
draw = ImageDraw.Draw(sheet)
y = 10
missing = []
for title, items in GROUPS:
    draw.text((12, y + 4), title, font=font, fill=(238, 238, 232))
    y += 34
    x = 10
    for item in items:
        path = SMALL / (item + '.png')
        if not path.exists():
            missing.append(item)
            x += SIZE
            continue
        with Image.open(path) as image:
            sheet.paste(image.convert('RGB').resize((SIZE, SIZE), Image.Resampling.LANCZOS), (x, y))
        draw.text((x + 6, y + SIZE - 24), item.replace('_BaseColor', '').replace('_Albedo', ''),
                  font=small, fill=(250, 240, 200))
        x += SIZE
    y += SIZE + 6
sheet.save(SMALL / '_candidates.png')

(GROUPS and (SMALL / 'preview-receipt.json').write_text(
    json.dumps({**report, 'missing': missing, 'sheet': str(SMALL / '_candidates.png')},
               ensure_ascii=False, indent=2), encoding='utf-8'))
print('NORMANDY_PREVIEW downscaled=%d missing=%s' % (report['downscaled'], missing))
print(json.dumps(report['rhaom_channels'], ensure_ascii=False, indent=2))
