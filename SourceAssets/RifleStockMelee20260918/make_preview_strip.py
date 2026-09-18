"""把 render_preview.py 渲染出的帧拼成对位胶片（系统 python + PIL）。

用法：python make_preview_strip.py Base [--reference]
带 --reference 时，右侧拼上参考视频同段帧（Reference/dense_frames）。
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

O = Path(__file__).resolve().parent
with_reference = '--reference' in sys.argv
profile = [a for a in sys.argv[1:] if not a.startswith('--')][0]
manifest = json.loads((O / 'animation.json').read_text(encoding='utf-8'))
contact = manifest['contact']

preview = sorted((O / 'Preview').glob('%s_t*.png' % profile))
if not preview:
    raise SystemExit('no preview frames for %s' % profile)

try:
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
except Exception:
    font = ImageFont.load_default()

CELL = (640, 360)
cols = 3
rows = (len(preview) + cols - 1) // cols
panels = [('本工程 M4 枪托砸击 · 作者源 clip', None)]

ref_dir = O / 'Reference' / 'dense_frames'
ref_frames = []
if with_reference:
    # 参考周期二：f_019(66.00) 起势 → f_023(66.27) 顶点 → f_025/f_027 扫击 → f_035(67.07) 回位
    ref_frames = [19, 21, 23, 25, 27, 29, 31, 33, 35]

strip = Image.new('RGB', (CELL[0] * cols, CELL[1] * ((rows * (2 if ref_frames else 1)) + (1 if ref_frames else 0))),
                  (12, 14, 18))
draw = ImageDraw.Draw(strip)

for i, path in enumerate(preview):
    t = int(path.stem.split('_t')[-1]) / 1000.0
    img = Image.open(path).convert('RGB')
    x, y = (i % cols) * CELL[0], (i // cols) * CELL[1]
    strip.paste(img, (x, y))
    draw.rectangle([x + 4, y + 4, x + 168, y + 32], fill=(0, 0, 0))
    draw.text((x + 8, y + 6), '%.2fs%s' % (t, '  接触' if abs(t - contact) < 1e-6 else ''), font=font,
              fill=(255, 230, 60))

if ref_frames:
    base = CELL[1] * rows + 24
    draw.text((8, base - 22), '参考 · BV13K421e7Rw 66.00–67.07s AK47 枪托近战', font=font, fill=(140, 220, 255))
    for i, f in enumerate(ref_frames):
        img = Image.open(ref_dir / ('f_%03d.png' % f)).convert('RGB').resize(CELL)
        x, y = (i % cols) * CELL[0], base + (i // cols) * CELL[1]
        strip.paste(img, (x, y))
        draw.rectangle([x + 4, y + 4, x + 130, y + 30], fill=(0, 0, 0))
        draw.text((x + 8, y + 6), '%.2fs' % ((f - 1) / 15.0 + 64.8), font=font, fill=(140, 220, 255))

suffix = '_vs_reference' if ref_frames else ''
dest = O / 'Preview' / ('%s_strip%s.png' % (profile, suffix))
strip.save(dest)
print('wrote', dest, strip.size)
