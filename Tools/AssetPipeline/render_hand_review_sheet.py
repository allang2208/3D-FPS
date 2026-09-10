import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

p=argparse.ArgumentParser()
p.add_argument('capture',type=Path)
p.add_argument('output',type=Path)
a=p.parse_args()
frames={int(f.stem.split('_')[-1]):f for f in (a.capture/'Frames').glob('Frame_*.png')}
canvas=Image.new('RGB',(1440,1800),(20,23,26))
draw=ImageDraw.Draw(canvas)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',19)
selected=[]
for i,n in enumerate([60,66,72,78,82,86,90,94,98,102,108,112]):
    k=min(frames,key=lambda j:abs(j-n))
    im=Image.open(frames[k]).convert('RGB')
    im=im.crop((im.width//2,im.height*4//9,im.width,im.height))
    im.thumbnail((480,420))
    x=i%3*480;y=i//3*450
    canvas.paste(im,(x,y))
    draw.text((x+8,y+424),f'UE frame {k:04d} | game t={2.8+k/10:.1f}s',font=font,fill='white')
    selected.append(frames[k].name)
a.output.parent.mkdir(parents=True,exist_ok=True)
canvas.save(a.output)
print(selected)
