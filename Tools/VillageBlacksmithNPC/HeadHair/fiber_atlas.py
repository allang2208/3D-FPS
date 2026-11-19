"""Make a photographic-scale salt-and-pepper fibre atlas for the smith's short hair cards."""
from pathlib import Path
import math
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[3] / 'SourceAssets/VillageBlacksmithNPC20261118/HeadHair'
TEX = ROOT / 'Textures'
TEX.mkdir(exist_ok=True, parents=True)
rng = random.Random(1811)
width, height = 2048, 1024
atlas = Image.new('RGBA', (width, height))
palettes = [
    [(32,27,23), (48,40,33), (62,52,44), (92,83,73)],
    [(48,43,39), (80,73,64), (104,101,94), (124,120,111)],
    [(36,31,28), (53,46,40), (76,69,60), (111,108,100)]
]
for j, palette in enumerate(palettes):
    layer = Image.new('RGBA', (512,1024))
    draw = ImageDraw.Draw(layer)
    # Draw individually tapered and offset fibres, from the root toward the tip.
    for i in range(175):
        root = rng.gauss(256, 85)
        spread = rng.uniform(-106,106)
        phase = rng.uniform(0,math.tau)
        tip = rng.uniform(.015,.38)
        bottom = rng.uniform(.91,.989)
        radius = rng.uniform(1.3,3.0)
        col = rng.choices(palette, weights=(.39,.27,.21,.13))[0]
        if j==1 and rng.uniform(0,1)<.22:
            col = (159,154,145)
        pts=[]
        for k in range(27):
            t=k/26
            x=root+spread*t+14*math.sin(phase+5*t)*math.sin(math.pi*t)+4*math.sin(t*9+phase)
            y=(bottom+(tip-bottom)*t)*1023
            pts.append((x,y))
        for k in range(26):
            draw.line((pts[k],pts[k+1]), fill=(*col,250), width=max(1,round(radius*(1-(k/26)**2.6))))
    atlas.paste(layer,(j*512,0))
# Continuous lightly grizzled grain, used only under the crown cards.
n=np.random.default_rng(118)
coarse=n.normal(0,5,(64,512))
coarse=np.asarray(Image.fromarray(np.uint8(np.clip(75+coarse*3,0,255))).resize((512,1024),Image.Resampling.BICUBIC)).astype(float)-75
fine=n.normal(0,3,(1024,512))
base=np.stack([40+coarse*.50+fine,35+coarse*.44+fine,30+coarse*.38+fine],axis=-1)
zone=Image.fromarray(np.uint8(np.clip(base,0,255))).convert('RGBA')
atlas.paste(zone,(1536,0))
atlas.save(TEX/'T_Smith_Fibres.png')
