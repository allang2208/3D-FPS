"""Assemble diagnostic renders of actual UE pose samples at playback speed."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/TentacleWhipV4')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
frames=[]
for frame in range(45,188,3):
    im=Image.open(OUT/f'pose_{frame:03}.png').convert('RGB');draw=ImageDraw.Draw(im);t=frame/60
    phase='待机' if t<1 else '向后蓄力' if t<2.1 else '向前甩出' if t<2.72 else '缠绕'
    draw.rectangle((0,0,im.width,34),fill=(20,23,29));draw.text((14,4),f'缚群 V4  |  {phase}  |  {t:.2f}s',font=font,fill=(230,235,238))
    draw.rectangle((0,im.height-31,im.width,im.height),fill=(20,23,29))
    draw.text((14,im.height-29),'UE 实际骨骼姿态的离线预览',font=font,fill=(190,200,211))
    frames.append(im)
frames[0].save(OUT/'whip_v4_preview.gif',save_all=True,append_images=frames[1:],duration=50,loop=0,optimize=False)
print(OUT/'whip_v4_preview.gif')
