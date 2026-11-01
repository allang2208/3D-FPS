from pathlib import Path
from PIL import Image,ImageDraw
O=Path(__file__).resolve().parent;frames=[]
for i in range(127):
 out=Image.new('RGB',(960,296),(25,28,32));d=ImageDraw.Draw(out)
 for j,role in enumerate(('reload','reload_mag10')):
  pic=Image.open(O/'PreviewFrames'/(role+f'_{i:03d}.png')).resize((480,270));out.paste(pic,(j*480,26));d.text((j*480+10,7),('M24 5-round' if j==0 else 'M24 10-round')+f'  {i/30:.2f}s  | authoring preview',fill='white')
 frames.append(out.quantize(colors=96))
frames[0].save(O/'M24_ReloadFlow_preview.gif',save_all=True,append_images=frames[1:],duration=[30 if i%3 else 40 for i in range(127)],loop=0,disposal=2)
print('Preview saved')
