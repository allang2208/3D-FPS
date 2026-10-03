"""Left/right, shipped/pre-fix comparison sheet of the PKM idle arms."""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\Elbow41\Review\idle_forearm')
COLS = (('shipped', 'l', 'shipped  LEFT'), ('shipped', 'r', 'shipped  RIGHT (control)'),
        ('prefix', 'l', 'pre-fix  LEFT'), ('prefix', 'r', 'pre-fix  RIGHT'))
CAMS = ('outer', 'inner', 'profile', 'along')
FRAME = 0

TILE = 420
LABEL = 20
sheet = Image.new('RGB', (len(COLS) * TILE, len(CAMS) * (TILE + LABEL)), (22, 22, 22))
draw = ImageDraw.Draw(sheet)

for r, cam in enumerate(CAMS):
    for c, (tag, side, name) in enumerate(COLS):
        p = OUT / tag / ('%s_%s_%04d.png' % (side, cam, FRAME))
        if not p.exists():
            continue
        img = Image.open(p).convert('RGB').resize((TILE, TILE))
        x, y = c * TILE, r * (TILE + LABEL)
        sheet.paste(img, (x, y))
        draw.text((x + 5, y + TILE + 3), '%-10s %s' % (cam, name), fill=(215, 215, 215))
        draw.rectangle([x, y, x + TILE - 1, y + TILE + LABEL - 1], outline=(70, 70, 70))

dest = OUT.parent / 'sheet_idle_forearm.png'
sheet.save(dest)
print('SHEET', dest, sheet.size)