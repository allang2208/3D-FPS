from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Polish20260922')
files=sorted((ROOT/'PreviewFrames').glob('*.png'));frames=[]
for i,p in enumerate(files):
    im=Image.open(p).convert('RGB');d=ImageDraw.Draw(im)
    d.rectangle((0,0,500,40),fill=(28,28,28));d.text((12,8),f'Authored throw | {min(1.5,i/15):.2f} s | release 0.75 s',fill='white')
    d.rectangle((0,584,500,610),fill=(28,28,28));d.text((12,590),'Pose preview: no UE cloth, staff or projectile simulation',fill='white')
    frames.append(im)
frames[0].save(ROOT/'throw_polish_preview.gif',save_all=True,append_images=frames[1:],duration=[67]*(len(frames)-1)+[700],loop=0)
sheet=Image.new('RGB',(1000,650),(28,28,28));d=ImageDraw.Draw(sheet)
for i,(filename,label) in enumerate([('before_Idle_1_front.png','Before: detached fragments / doubled shell'),('after_Idle_000.png','After: connected robe / fitted inner fabric')]):
    im=Image.open(ROOT/filename).convert('RGB');im.thumbnail((500,605));sheet.paste(im,(i*500+(500-im.width)//2,38))
    d.text((i*500+10,12),label,fill='white')
sheet.save(ROOT/'garment_comparison.jpg',quality=88)
print('Saved comparison sheet and authored throw GIF; no engine cloth simulation')
