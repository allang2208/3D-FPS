from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
frames=[]
meta=json.loads((ROOT/'diagnostic_render.json').read_text())
for i in range(meta['frames']):
    im=Image.new('RGB',(640,450),(24,28,33));d=ImageDraw.Draw(im)
    d.text((14,10),'同一蒙皮：保留源动作头身配合',font=font,fill='white')
    d.text((334,10),'同一蒙皮：叠加当前头部锁定',font=font,fill='white')
    for x,key in [(0,'SourceHeadMotion'),(320,'CurrentLockedHead')]:
        im.paste(Image.open(ROOT/f'Frames/{key}/{i:03d}.png'),(x,40))
    d.text((14,427),f'离线诊断对照 / Walk_A / 原速 / {i/meta["fps"]:.3f}s',font=small,fill=(180,190,200))
    frames.append(im)
frames[0].save(ROOT/'Head_Motion_Diagnostic.gif',save_all=True,append_images=frames[1:],duration=round(1000/meta['fps']),loop=0)
sheet=Image.new('RGB',(1280,450));sheet.paste(frames[8],(0,0));sheet.paste(frames[16],(640,0));sheet.save(ROOT/'Head_Motion_ContactSheet.png')
im=Image.new('RGB',(1280,440),(24,28,33));d=ImageDraw.Draw(im)
for i,label in enumerate(['原始绑定姿势','左肘 90° 单关节','左膝 90° 单关节','左肩 60° 单关节']):
    im.paste(Image.open(ROOT/f'Frames/JointProbes/{i:03d}.png'),(i*320,40))
    d.text((i*320+12,10),label,font=font,fill='white')
im.save(ROOT/'Joint_Probes.png')
print('Diagnostic composites saved')
