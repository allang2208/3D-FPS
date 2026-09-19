from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path('D:/FPS3D/FPSGAME')
out = root / 'SourceAssets/M4HipFraming20260909'
panels = [
    ('Godot 原版腰射参考', out / 'godot_infima_ar_hip.png'),
    ('UE 修改前', root / 'Saved/GunplayUpgrade/m4-rig-final-dx12-60/10_Final_Recovered.png'),
    ('UE 修改后', root / 'Saved/GunplayUpgrade/m4-hip-final60/10_Final_Recovered.png'),
]
sheet = Image.new('RGB', (1920, 410), (25, 30, 35))
draw = ImageDraw.Draw(sheet)
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 23)
for index, (label, source) in enumerate(panels):
    with Image.open(source) as image:
        sheet.paste(image.convert('RGB').resize((640, 360), Image.Resampling.LANCZOS), (index * 640, 50))
    draw.text((index * 640 + 18, 12), label, font=font, fill='white')
sheet.save(out / 'hip_framing_comparison.png')
