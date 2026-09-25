"""Native-rate frames of one continuous forward spin from the tutorial P1 cache."""
import json
import sys
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

HERE = Path(__file__).parent
VIDEO = HERE.parents[1] / 'PivotStudy20260915' / 'p1_reference_video_only.mp4'
START = float(sys.argv[1]) if len(sys.argv) > 1 else 146.80
END = float(sys.argv[2]) if len(sys.argv) > 2 else 148.60
TAG = sys.argv[3] if len(sys.argv) > 3 else 'cycle'
CROP = (0, 20, 440, 460)
CELL = 220
COLUMNS = 8

capture = cv2.VideoCapture(str(VIDEO))
fps = capture.get(cv2.CAP_PROP_FPS)
count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
first = int(START * fps)
last = int(END * fps)
capture.set(cv2.CAP_PROP_POS_FRAMES, first)
out = HERE / TAG
out.mkdir(exist_ok=True)
cells = []
index_rows = []
for number in range(first, last + 1):
    ok, frame = capture.read()
    if not ok:
        break
    seconds = number / fps
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    image.save(out / ('f%05d.png' % number))
    crop = image.crop(CROP).resize((CELL, CELL), Image.LANCZOS)
    draw = ImageDraw.Draw(crop)
    draw.rectangle((0, 0, CELL, 16), fill=(15, 15, 18))
    draw.text((4, 2), '%d  %.3fs' % (number - first, seconds), fill=(240, 240, 240))
    cells.append(crop)
    index_rows.append({'index': number - first, 'frame': number, 'seconds': round(seconds, 4)})

rows = (len(cells) + COLUMNS - 1) // COLUMNS
sheet = Image.new('RGB', (COLUMNS * CELL, rows * CELL), (10, 10, 12))
for i, cell in enumerate(cells):
    sheet.paste(cell, ((i % COLUMNS) * CELL, (i // COLUMNS) * CELL))
sheet_path = HERE / ('%s_sheet.jpg' % TAG)
sheet.save(sheet_path, quality=72)
(HERE / ('%s_frames.json' % TAG)).write_text(json.dumps({
    'video': str(VIDEO), 'fps': fps, 'frame_count': count,
    'size': [width, height], 'start': START, 'end': END,
    'crop': CROP, 'frames': index_rows,
}, indent=2), encoding='utf-8')
print('fps', fps, 'frames', len(cells), 'size', width, height, 'sheet', sheet_path, sheet_path.stat().st_size)
