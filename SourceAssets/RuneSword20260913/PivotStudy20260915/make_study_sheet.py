"""Compose a short, attributed sequence of actual source frames for motion study."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).parent
FONT = 'C:/Windows/Fonts/msyh.ttc'
title_font = ImageFont.truetype(FONT, 27)
label_font = ImageFont.truetype(FONT, 22)
small_font = ImageFont.truetype(FONT, 17)
items = [
    (10, '147.000', '1  闭握 · 准备启动'),
    (11, '147.200', '2  手腕带动 · 松指'),
    (12, '147.400', '3  手柄经过 · 手指让位'),
    (13, '147.600', '4  翻掌 · 剑尖朝下'),
    (15, '148.000', '5  手柄回转 · 手掌跟随'),
    (17, '148.400', '6  合指回握 · 收住'),
]
sheet = Image.new('RGB', (1260, 990), '#151b23')
draw = ImageDraw.Draw(sheet)
draw.text((20, 16), '正向转刀：观察护手下方的握柄与手部接触关系', font=title_font, fill='#edf1f5')
draw.text((20, 57), '原视频 P1 / 02:27–02:28.4 · 按时间顺序排列，帧间隔不等', font=small_font, fill='#aebdcd')
for k, (index, seconds, label) in enumerate(items):
    source = Image.open(ROOT / 'Continuous' / f'frame_{index:03d}.png').convert('RGB')
    # Include the entire moving hand and wrist. Preserve source aspect ratio.
    crop = source.crop((155, 85, 465, 350))
    frame = ImageOps.contain(crop, (400, 342), Image.Resampling.LANCZOS)
    x, y = 10 + (k % 3) * 420, 96 + (k // 3) * 424
    sheet.paste(frame, (x, y))
    draw.text((x + 5, y + 349), label, font=label_font, fill='#edf1f5')
    draw.text((x + 5, y + 383), f'P1  {seconds} s', font=small_font, fill='#9db5cc')
draw.text((20, 947), '参考来源：bilibili.com/video/BV1zz4y117f6/ · 原始画面裁切，仅作动作分析', font=small_font, fill='#aebdcd')
sheet.save(ROOT / 'contact_sequence.jpg', quality=95)

