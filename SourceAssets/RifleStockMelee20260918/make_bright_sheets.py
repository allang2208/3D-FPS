"""把 30 fps 参考帧提亮后拼图（夜景原帧太暗，看不清枪的结构）。

用旧读谱同一口径：每通道 out = clip(2.4*in + 40)。
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DIR = Path(__file__).resolve().parent
SRC = DIR / 'Reference' / 'f30'
OUT = DIR / 'Reference' / 'Bright'
OUT.mkdir(parents=True, exist_ok=True)

try:
    FONT = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 26)
except Exception:
    FONT = ImageFont.load_default()

CROP = (330, 120, 1280, 660)      # 视模区域
CELL = (640, 365)
GAIN = [min(255, int(2.4 * v + 40)) for v in range(256)]

SHEETS = {
    'bright_cock_66.10-66.27': range(94, 100),      # 蓄势顶点
    'bright_sweep_66.33-66.50': range(101, 107),    # 扫击前段
    'bright_sweep_66.53-66.70': range(107, 113),    # 扫击后段
}

for name, frames in SHEETS.items():
    count = len(list(frames))
    frames = list(frames)
    sheet = Image.new('RGB', (CELL[0] * count, CELL[1]), (0, 0, 0))
    for index, frame in enumerate(frames):
        image = Image.open(SRC / ('f_%04d.png' % frame)).convert('RGB').crop(CROP).resize(CELL, Image.LANCZOS)
        image = image.point(GAIN * 3)
        sheet.paste(image, (index * CELL[0], 0))
        draw = ImageDraw.Draw(sheet)
        draw.rectangle([index * CELL[0] + 4, 4, index * CELL[0] + 190, 36], fill=(0, 0, 0))
        draw.text((index * CELL[0] + 8, 6), '%.3fs' % (63.0 + (frame - 1) / 30.0), font=FONT, fill=(255, 230, 60))
    dest = OUT / ('%s.png' % name)
    sheet.save(dest)
    print(dest, sheet.size)
