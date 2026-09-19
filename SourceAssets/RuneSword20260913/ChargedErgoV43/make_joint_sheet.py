"""Contact sheet of the left-joint review shots plus the accepted V22 images."""
from pathlib import Path
from PIL import Image, ImageDraw

P = Path(__file__).parent
SHOTS = [
    'HeavyCharge_000ms', 'HeavyCharge_120ms', 'HeavyCharge_200ms', 'HeavyCharge_350ms',
    'HeavyCharge_650ms', 'HeavyCharge_1000ms', 'HeavyCharge_1400ms', 'HeavyCharge_1600ms',
    'HeavyCharge_2000ms', 'HeavyRelease_020ms', 'HeavyRelease_075ms', 'HeavyRelease_150ms',
    'HeavyRelease_400ms', 'HeavyRelease_600ms', 'HeavyRelease_800ms', 'HeavyRelease_1000ms',
]
accepted = [
    (P.parent / 'ChargedArmV22/Review_ChargedArmV22/raised_left_joint.png', 'ACCEPTED V22 650ms'),
    (P.parent / 'ChargedArmV22/Review_ChargedArmV22/charged_left_joint.png', 'ACCEPTED V22 2000ms'),
    (P.parent / 'ChargedArmV22/Review_ChargedArmV22/strike_left_joint.png', 'ACCEPTED V22 release 60ms'),
    (P.parent / 'ChargedArmV22/Review_ChargedArmV22/recovery_left_joint.png', 'ACCEPTED V22 release 400ms'),
]
COLUMNS = 4
LABEL = 24

tiles = []
captions = []
for name in SHOTS:
    tiles.append(Image.open(P / 'Review' / (name + '_left_joint.png')).convert('RGB'))
    captions.append(name)
for path, caption in accepted:
    tiles.append(Image.open(path).convert('RGB'))
    captions.append(caption)

cell = (640, 400)
rows = (len(tiles) + COLUMNS - 1) // COLUMNS
sheet = Image.new('RGB', (COLUMNS * cell[0], rows * (cell[1] + LABEL)), (16, 18, 22))
draw = ImageDraw.Draw(sheet)
for index, (tile, caption) in enumerate(zip(tiles, captions)):
    x = (index % COLUMNS) * cell[0]
    y = (index // COLUMNS) * (cell[1] + LABEL)
    draw.text((x + 6, y + 6), caption, fill=(240, 240, 240))
    sheet.paste(tile.resize(cell, Image.LANCZOS), (x, y + LABEL))
sheet.save(P / 'Review' / 'sheet_left_joint.png')
print('SHEET', sheet.size)
