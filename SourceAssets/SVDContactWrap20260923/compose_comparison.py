"""Lay out the actual local before/after renders authorized by the user."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

O = Path(__file__).parent / 'ContactViews'
canvas = Image.new('RGB', (1200, 1993), '#24272b')
draw = ImageDraw.Draw(canvas)
font_path = 'C:/Windows/Fonts/msyh.ttc'
title = ImageFont.truetype(font_path, 31)
label = ImageFont.truetype(font_path, 24)
note = ImageFont.truetype(font_path, 20)
draw.text((28, 17), 'SVD 持匣手型 · 源模型局部对照', font=title, fill='white')
draw.text((225, 74), '调整前', font=label, fill='#dadde1')
draw.text((820, 74), '本轮调整', font=label, fill='#dadde1')
for row, (view, caption) in enumerate([('palm', '四指包覆'), ('thumb', '拇指对握'), ('fingers', '手背关节')]):
    y = 116 + row * 603
    for col, version in enumerate(['before', 'after']):
        picture = Image.open(O / f'{version}_{view}.jpg').resize((590, 590), Image.Resampling.LANCZOS)
        canvas.paste(picture, (5 + col * 600, y))
    draw.rounded_rectangle((16, y + 12, 205, y + 49), radius=5, fill='#24272b')
    draw.text((27, y + 15), caption, font=label, fill='#eeeeee')
draw.text((22, 1936), '局部裁切、统一展示材质；非游戏画面。腕部截面为展示裁切边界。', font=note, fill='#c9ced4')
canvas.save(O / 'SVD_Grip_Before_After.jpg', quality=92)
