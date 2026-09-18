"""把 30 fps 参考帧拼成 3×3 读谱大图（每格 640×360 原尺寸）。

python make_f30_sheets.py            # 默认输出一个完整挥击周期 4 张
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DIR = Path(__file__).resolve().parent
SRC = DIR / 'Reference' / 'f30'
OUT = DIR / 'Reference' / 'Sheets'
OUT.mkdir(parents=True, exist_ok=True)

try:
    FONT = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 26)
except Exception:
    FONT = ImageFont.load_default()

# 原生 1280×720；视模在画面中下偏右，裁掉左侧与顶部后缩到 640×360 一格，
# 有效分辨率仍高于早先的 640×360 整帧。
CROP = (330, 150, 1280, 720)
CELL = (640, 360)

# 一个完整挥击周期（66.00–67.17 s）按 1/30 s 铺开
RANGES = {
    'c2_00_66.00-66.27': range(91, 100),
    'c2_01_66.30-66.57': range(100, 109),
    'c2_02_66.60-66.87': range(109, 118),
    'c2_03_66.90-67.17': range(118, 127),
}

for name, frames in RANGES.items():
    sheet = Image.new('RGB', (CELL[0] * 3, CELL[1] * 3), (0, 0, 0))
    for index, frame in enumerate(frames):
        path = SRC / ('f_%04d.png' % frame)
        if not path.exists():
            continue
        image = Image.open(path).convert('RGB').crop(CROP).resize(CELL, Image.LANCZOS)
        x, y = (index % 3) * CELL[0], (index // 3) * CELL[1]
        sheet.paste(image, (x, y))
        draw = ImageDraw.Draw(sheet)
        draw.rectangle([x + 4, y + 4, x + 170, y + 34], fill=(0, 0, 0))
        draw.text((x + 8, y + 6), '%.3fs' % (63.0 + (frame - 1) / 30.0), font=FONT, fill=(255, 230, 60))
    dest = OUT / ('%s.png' % name)
    sheet.save(dest)
    print(dest, sheet.size)
