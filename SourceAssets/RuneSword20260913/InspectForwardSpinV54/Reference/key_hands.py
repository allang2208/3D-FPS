"""Full-resolution crops of the key hand phases in one forward spin."""
import json
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).parent
meta = json.loads((HERE / 'cycle_frames.json').read_text(encoding='utf-8'))
by_index = {row['index']: row for row in meta['frames']}
PICKS = [
    (4, 'closed grip'),
    (10, 'wrist throw, loosen'),
    (16, 'hilt passes fingers'),
    (21, 'tip down, palm opens'),
    (26, 'open palm, hang'),
    (32, 'hilt forward-up, palm follows'),
    (37, 'hilt forward, palm under'),
    (43, 'fingers close'),
]
BOX = (40, 60, 400, 420)
CELL = 330
cells = []
for index, label in PICKS:
    row = by_index[index]
    image = Image.open(HERE / 'cycle' / ('f%05d.png' % row['frame'])).convert('RGB')
    crop = image.crop(BOX).resize((CELL, CELL), Image.LANCZOS)
    draw = ImageDraw.Draw(crop)
    draw.rectangle((0, 0, CELL, 18), fill=(15, 15, 18))
    draw.text((4, 3), '#%d %.3fs %s' % (index, row['seconds'], label), fill=(240, 240, 240))
    cells.append(crop)
sheet = Image.new('RGB', (4 * CELL, 2 * CELL), (10, 10, 12))
for i, cell in enumerate(cells):
    sheet.paste(cell, ((i % 4) * CELL, (i // 4) * CELL))
path = HERE / 'key_hands.jpg'
sheet.save(path, quality=78)
print(path, path.stat().st_size)
