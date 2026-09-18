"""放大裁剪：判断蓄势帧里枪口与枪托各自的方向（读谱用，2x 放大）。

输出 Reference/Sheets/zoom_<tag>.png。
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DIR = Path(__file__).resolve().parent
SRC = DIR / 'Reference' / 'dense_frames'
OUT = DIR / 'Reference' / 'Sheets'
OUT.mkdir(parents=True, exist_ok=True)

try:
    FONT = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 30)
except Exception:
    FONT = ImageFont.load_default()

CROP = (330, 50, 640, 300)   # 第一人称视模在扫击段所在的中右区
ZOOM = 4

SHEETS = {
    'zoom_cock': [21, 23, 25, 27],
    'zoom_sweep': [26, 28, 30, 32],
}

for name, frames in SHEETS.items():
    w, h = (CROP[2] - CROP[0]) * ZOOM, (CROP[3] - CROP[1]) * ZOOM
    sheet = Image.new('RGB', (w * 2, h * 2), (0, 0, 0))
    for i, f in enumerate(frames):
        img = Image.open(SRC / ('f_%03d.png' % f)).convert('RGB').crop(CROP)
        img = img.resize((w, h), Image.LANCZOS)
        x, y = (i % 2) * w, (i // 2) * h
        sheet.paste(img, (x, y))
        draw = ImageDraw.Draw(sheet)
        draw.rectangle([x + 6, y + 6, x + 210, y + 48], fill=(0, 0, 0))
        draw.text((x + 12, y + 10), 'f_%03d  %.2fs' % (f, (f - 1) / 15.0 + 64.8), font=FONT, fill=(255, 255, 0))
    dest = OUT / (name + '.png')
    sheet.save(dest)
    print(dest, sheet.size)
