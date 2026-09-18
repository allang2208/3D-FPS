"""把 BV13K421e7Rw 的密集帧拼成读谱用的大图（2x2，每格 640x360 原尺寸）。

只做读谱用的拼图，不改参考帧本身。输出在 Reference/Sheets/。
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DIR = Path(__file__).resolve().parent
SRC = DIR / 'Reference' / 'dense_frames'
OUT = DIR / 'Reference' / 'Sheets'
OUT.mkdir(parents=True, exist_ok=True)

try:
    FONT = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 26)
except Exception:
    FONT = ImageFont.load_default()

SHEETS = {
    # 两个完整挥击周期，每张 3x3、每格 640x360 原尺寸
    'cycle_1_6480_6587': [1, 3, 5, 7, 9, 11, 13, 15, 17],
    'cycle_2_6600_6707': [19, 21, 23, 25, 27, 29, 31, 33, 35],
}

for name, frames in SHEETS.items():
    sheet = Image.new('RGB', (640 * 3, 360 * 3), (0, 0, 0))
    for i, f in enumerate(frames):
        img = Image.open(SRC / ('f_%03d.png' % f)).convert('RGB')
        x, y = (i % 3) * 640, (i // 3) * 360
        sheet.paste(img, (x, y))
        draw = ImageDraw.Draw(sheet)
        draw.rectangle([x + 4, y + 4, x + 176, y + 40], fill=(0, 0, 0))
        draw.text((x + 10, y + 8), 'f_%03d  %.2fs' % (f, (f - 1) / 15.0 + 64.8), font=FONT, fill=(255, 255, 0))
    dest = OUT / (name + '.png')
    sheet.save(dest)
    print(dest, sheet.size)
