from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent;font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22);frames=[]
for f in range(0,56,2):
 im=Image.new('RGB',(1280,464),(24,29,36));draw=ImageDraw.Draw(im)
 for x,stage,label in [(0,'before','修复前 · 源动作'),(640,'after','修复后 · 源动作')]:
  im.paste(Image.open(O/'Compare'/f'{stage}_{f:03d}.png'),(x,44));draw.text((x+16,10),label,fill=(228,236,242),font=font)
 frames.append(im)
frames[0].save(O/'M24_Thumb_Before_After.gif',save_all=True,append_images=frames[1:],duration=100,loop=0,optimize=True)
frames[10].save(O/'M24_Thumb_Before_After.png')
print('M24 thumb comparison saved')
