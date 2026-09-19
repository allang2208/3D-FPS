"""Compose the left-elbow review shots into two contact sheets."""
from pathlib import Path
from PIL import Image, ImageDraw

P = Path(__file__).parent / 'Review'
SHOTS = [
    'HeavyCharge_000ms', 'HeavyCharge_120ms', 'HeavyCharge_200ms',
    'HeavyCharge_350ms', 'HeavyCharge_650ms', 'HeavyCharge_1000ms',
    'HeavyCharge_1400ms', 'HeavyCharge_1600ms', 'HeavyCharge_2000ms',
    'HeavyRelease_020ms', 'HeavyRelease_075ms', 'HeavyRelease_150ms',
    'HeavyRelease_400ms', 'HeavyRelease_600ms', 'HeavyRelease_800ms',
    'HeavyRelease_1000ms',
]
COLUMNS = 4

for view in ('elbow_outside', 'elbow_axial'):
    tiles = [Image.open(P / (name + '_' + view + '.png')).convert('RGB') for name in SHOTS]
    width, height = tiles[0].size
    label = 22
    rows = (len(tiles) + COLUMNS - 1) // COLUMNS
    sheet = Image.new('RGB', (COLUMNS * width, rows * (height + label)), (18, 20, 24))
    draw = ImageDraw.Draw(sheet)
    for index, (name, tile) in enumerate(zip(SHOTS, tiles)):
        x = (index % COLUMNS) * width
        y = (index // COLUMNS) * (height + label)
        draw.text((x + 6, y + 5), name, fill=(235, 235, 235))
        sheet.paste(tile, (x, y + label))
    sheet.save(P / ('sheet_' + view + '.png'))
    print('SHEET', view, sheet.size)

FP = Path(__file__).parent / 'ReviewFP'
FP_SHOTS = [
    'HeavyCharge_000ms', 'HeavyCharge_120ms', 'HeavyCharge_200ms', 'HeavyCharge_300ms',
    'HeavyCharge_400ms', 'HeavyCharge_500ms', 'HeavyCharge_650ms', 'HeavyCharge_900ms',
    'HeavyCharge_1200ms', 'HeavyCharge_1600ms', 'HeavyCharge_2000ms',
    'HeavyRelease_020ms', 'HeavyRelease_075ms', 'HeavyRelease_150ms', 'HeavyRelease_400ms',
    'HeavyRelease_600ms', 'HeavyRelease_800ms', 'HeavyRelease_1000ms',
]
for view in ('fp', 'outside'):
    tiles = [Image.open(FP / (name + '_' + view + '.png')).convert('RGB') for name in FP_SHOTS]
    width, height = tiles[0].size
    label = 22
    rows = (len(tiles) + COLUMNS - 1) // COLUMNS
    sheet = Image.new('RGB', (COLUMNS * width, rows * (height + label)), (18, 20, 24))
    draw = ImageDraw.Draw(sheet)
    for index, (name, tile) in enumerate(zip(FP_SHOTS, tiles)):
        x = (index % COLUMNS) * width
        y = (index // COLUMNS) * (height + label)
        draw.text((x + 6, y + 5), name, fill=(235, 235, 235))
        sheet.paste(tile, (x, y + label))
    sheet.save(FP / ('sheet_' + view + '.png'))
    print('SHEET', view, sheet.size)
