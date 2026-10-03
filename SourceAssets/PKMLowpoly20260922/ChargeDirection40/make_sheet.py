"""Contact sheet of the first-person PKM empty-reload frames."""
import json
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\ChargeDirection40')
SRC = HERE / 'Review' / 'base'
OUT = HERE / 'Review' / 'sheet_empty_reload.png'

data = json.loads((HERE / 'fps_view_base.json').read_text(encoding='utf-8'))
rows = {r['frame']: r for r in data['rows']}
frames = sorted(rows)

COLS, TILE_W = 4, 480
TILE_H = int(TILE_W * 9 / 16)
LABEL = 22
ROWS = (len(frames) + COLS - 1) // COLS
sheet = Image.new('RGB', (COLS * TILE_W, ROWS * (TILE_H + LABEL)), (24, 24, 24))
draw = ImageDraw.Draw(sheet)

for i, f in enumerate(frames):
    img = Image.open(SRC / ('fp_%04d.png' % f)).convert('RGB').resize((TILE_W, TILE_H))
    cx, cy = (i % COLS) * TILE_W, (i // COLS) * (TILE_H + LABEL)
    sheet.paste(img, (cx, cy))
    r = rows[f]
    def fmt(p):
        return '(%+.2f,%+.2f)' % (p[0], p[1]) if p[0] == p[0] else '(off)'
    text = '%4.2fs  L%s  R%s' % (r['sec'], fmt(r['hand_screen']),
                                 fmt([r['elbow_screen'][0], r['hand_screen'][1]]))
    draw.text((cx + 4, cy + TILE_H + 4), text, fill=(210, 210, 210))
    draw.rectangle([cx, cy, cx + TILE_W - 1, cy + TILE_H + LABEL - 1],
                   outline=(70, 70, 70))

sheet.save(OUT)
print('SHEET', OUT, sheet.size)