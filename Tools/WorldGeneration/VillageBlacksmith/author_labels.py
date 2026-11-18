"""Create legible painted shop-name textures at the board's real aspect ratio."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np

out=Path(__file__).resolve().parents[3]/'SourceAssets/HillsVillageBlacksmith20261117/Authored'
out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(171117)
for name,label,w,h in [('BlacksmithSign','铁匠铺',1000,440),('ClosedPlaque','待修复',960,400)]:
    grain=rng.normal(0,3,(h,w))+np.sin(np.arange(h)[:,None]*.19)*5
    pixels=np.stack([np.clip(base+grain,0,255) for base in (58,43,29)],axis=2).astype('uint8')
    im=Image.fromarray(pixels);draw=ImageDraw.Draw(im)
    draw.rounded_rectangle((12,12,w-13,h-13),radius=8,outline=(144,117,74),width=6)
    font=ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc',190 if name=='BlacksmithSign' else 198)
    draw.text((w*.53,h*.53),label,font=font,fill=(219,203,158),anchor='mm',stroke_width=1)
    if name=='BlacksmithSign':
        # Small forged anvil emblem, not additional text competing with the name.
        draw.polygon([(38,175),(126,175),(150,194),(105,205),(105,245),(132,260),(50,260),(72,242),(72,203),(40,195)],fill=(187,172,134))
    im.save(out/('T_'+name+'.png'))
