"""Repaint the sound village sign's two oak planks, preserving its fixing atlas."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT/'SourceAssets/HillsVillageTavern/Sign'
OUT = ROOT/'SourceAssets/HillsVillageBakery/Furnishings'
OUT.mkdir(exist_ok=True, parents=True)
W, H = 2048, 896
channels = ['Color','Normal','ORM']
atlas = {key:np.array(Image.open(SOURCE/f'T_TavernSign_{key}.png').convert('RGB')) for key in channels}

# Use the clean oak from the donor's wood edge strip on both carved boards.
# The iron straps, nails, rim, backside and endgrain retain their original UVs.
oak = {}
for key, image in atlas.items():
    strip = image[1796:1959]
    rows = []
    for shift, flip in [(289,False),(10,True),(676,False),(1219,True)]:
        part = np.roll(strip, shift, axis=1)
        rows.append(part[::-1] if flip else part)
    oak[key] = np.array(Image.fromarray(np.vstack(rows)).resize((W,H),Image.Resampling.BICUBIC))

Y,X = np.mgrid[0:H,0:W]
color = oak['Color'].astype(float)
luminance = color.mean(axis=2)
ink = Image.new('L',(W,H))
draw = ImageDraw.Draw(ink)
# Long, slightly asymmetrical country loaf, three hand-scored cuts and a wheat stalk.
draw.polygon([(245,503),(248,472),(260,442),(291,405),(337,372),(379,357),
              (433,346),(488,350),(541,372),(573,401),(594,438),(598,472),
              (579,492),(528,514),(453,535),(365,545),(291,537),(258,524)],fill=246)
for x,y,h in [(336,441,52),(401,418,58),(468,410,46)]:
    draw.line([(x-22,y+h//2),(x-6,y+4),(x+20,y-h//2)],fill=0,width=12,joint='curve')
draw.line([(255,577),(317,599),(383,602),(447,592),(520,560),(574,523)],
          fill=211,width=7,joint='curve')
for x,y in [(432,585),(472,572),(511,553),(547,532)]:
    draw.polygon([(x,y),(x+12,y-22),(x+21,y-36),(x+18,y-14)],fill=214)
    draw.polygon([(x,y),(x+13,y+2),(x+31,y-2),(x+21,y-9)],fill=202)
font=ImageFont.truetype('C:/Windows/Fonts/simkai.ttf',325)
for char, x in [('面',884),('包',1231),('屋',1583)]:
    a,b,c,d=draw.textbbox((0,0),char,font=font)
    # The sign face is 85:44 mapped to 2040:888. Compensate the
    # non-square physical texels in the atlas when drawing the lettering.
    patch=Image.new('L',(c-a+8,d-b+8))
    ImageDraw.Draw(patch).text((4-a,4-b),char,font=font,fill=247,stroke_width=1)
    patch=patch.resize((round(patch.width*1.18),patch.height),Image.Resampling.LANCZOS)
    ink.paste(patch,(x-patch.width//2,451-patch.height//2))
for y in (150,736):
    draw.line([(425,y),(762,y)],fill=148,width=5)
    draw.line([(1308,y),(1618,y)],fill=148,width=5)
    draw.line([(795,y),(1239,y)],fill=125,width=3)
    for cx in (778,1256):
        draw.polygon([(cx-10,y),(cx,y-5),(cx+10,y),(cx,y+5)],fill=192)
marks=np.asarray(ink,dtype=float)/255
rng=np.random.default_rng(12218)
blotch=np.array(Image.fromarray(rng.integers(0,255,(159,175),dtype=np.uint8)).resize((W,H),Image.Resampling.BICUBIC))/255.
edge=np.clip(np.minimum.reduce((X,W-1-X,Y,H-1-Y))/48.,0,1)
wear=np.clip((luminance-44)/44.,0,1)*np.clip(blotch*1.6+.20,0.,1.)
wash=(.59+.21*blotch)*edge
ground=np.stack((luminance*.52+27,luminance*.26+15,luminance*.21+12),axis=-1)
color=color*(1-wash[:,:,None])+ground*wash[:,:,None]
alpha=marks*wear*.97
color=color*(1-alpha[:,:,None])+np.array([230,199,131])*alpha[:,:,None]
normal=oak['Normal'].astype(float)
dy,dx=np.gradient(alpha)
normal[:,:,0]-=29*dx
normal[:,:,1]-=29*dy
orm=oak['ORM'].astype(float)
orm[:,:,1]=np.clip(orm[:,:,1]-12*wash-17*alpha,115,250)
for key,face in [('Color',color),('Normal',normal),('ORM',orm)]:
    atlas[key][:H]=np.uint8(np.clip(face,0,255))
    Image.fromarray(atlas[key]).save(OUT/f'T_BakerySign_{key}.png')
