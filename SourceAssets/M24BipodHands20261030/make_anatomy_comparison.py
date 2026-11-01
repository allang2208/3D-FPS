"""Compose the actual offline render frames; no generated replacement imagery."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent/'Review'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
def pair(index,scale=1):
    w,h=640*scale,400*scale
    out=Image.new('RGB',(w*2,h+56),(25,29,35));draw=ImageDraw.Draw(out)
    for col,(label,caption) in enumerate((('AnatomyPrevious','修改前'),('AnatomyFinal','本次修订'))):
        im=Image.open(O/label/f'motion_{index:02d}.png').convert('RGB').resize((w,h))
        out.paste(im,(col*w,56));draw.text((col*w+12,6),caption,font=font,fill=(240,240,240))
    draw.text((12,32),'固定视角离线蒙皮；相同时间点；非游戏截图',font=small,fill=(177,186,196))
    return out
pair(15).save(O/'anatomy_comparison.jpg',quality=91)
frames=[pair(i).resize((960,342)) for i in range(30)]
frames[0].save(O/'anatomy_comparison_slow.gif',save_all=True,append_images=frames[1:],duration=[500]+[50]*28+[500],loop=0,optimize=True)
# A compact strip for inspection of the full reach, pull and return.
strip=Image.new('RGB',(1280,456*4),(25,29,35))
for row,i in enumerate((4,9,15,22)):strip.paste(pair(i),(0,row*456))
strip.save(O/'anatomy_sequence.jpg',quality=88)
print('ANATOMY_COMPARISON_READY',flush=True)
