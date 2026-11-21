"""Paint the apothecary emblem on the village fascia's intact and broken UV islands."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


SOURCE = Path(__file__).resolve().parents[3] / 'SourceAssets'
DEST = SOURCE / 'HillsVillageHerbalist/Sign'
TIMBER = SOURCE / 'HillsVillageTavern/Sign'
W, H = 2048, 896


def emblem():
    mask = Image.new('L', (W, H))
    pen = ImageDraw.Draw(mask)
    # Open mortar, foot, and pestle. The botanical sprig remains legible at a distance.
    pen.line([(250,435),(270,495),(304,546),(353,571),(434,571),(479,547),
              (515,499),(536,435)], fill=244, width=19, joint='curve')
    pen.ellipse((244,411,541,456), outline=244, width=16)
    pen.line([(365,573),(356,605),(326,616),(326,627),(461,627),
              (461,616),(429,605),(421,573)], fill=238, width=14, joint='curve')
    pen.line([(391,422),(503,296)], fill=248, width=22)
    pen.ellipse((487,279,530,322), fill=246)
    pen.line([(357,424),(330,357),(315,303),(310,266)], fill=230, width=9)
    for polygon in [
        [(315,313),(285,299),(264,261),(283,269),(306,287)],
        [(324,345),(350,321),(360,283),(337,302),(324,325)],
        [(336,375),(300,360),(279,324),(312,341)],
        [(345,402),(371,381),(384,344),(361,360)],
        [(312,286),(296,259),(300,224),(313,245)],
    ]:
        pen.polygon(polygon, fill=236)
    font = ImageFont.truetype('C:/Windows/Fonts/simkai.ttf', 373)
    for letter, x in zip('草药铺', (805,1240,1675)):
        l,t,r,b = font.getbbox(letter)
        pen.text((x-(l+r)/2, H*.51-(t+b)/2), letter, font=font, fill=252, stroke_width=1)
    for y in (98,H-98):
        pen.line((245,y,1798,y), fill=156, width=5)
    return np.asarray(mask, dtype=np.float32)/255


def face(mask, damaged):
    rng = np.random.default_rng(1538 if damaged else 1537)
    def noise(w,h):
        pixels = Image.fromarray(rng.integers(0,256,(h,w),dtype=np.uint8))
        return np.asarray(pixels.resize((W,H), Image.Resampling.BICUBIC),dtype=np.float32)/255
    y,x = np.mgrid[:H,:W].astype(np.float32)
    x,y = x/W,y/H
    fibres, grain, fade = noise(110,H),noise(28,235),noise(35,32)
    rings = (.5+.5*np.sin(y*840+7*np.sin(x*3+y*12)+4*noise(6,10)))**6
    split = np.zeros_like(x)
    for _ in range(50 if damaged else 24):
        cx,cy = rng.uniform(0,1,2)
        length = rng.uniform(.025,.15)
        line = cy+.0014*np.sin((x-cx)*43)
        split = np.maximum(split,np.clip(1-abs(y-line)*650,0,1)*np.clip(1-abs(x-cx)/length,0,1))
    texture = 22*(fibres-.5)+28*(grain-.5)+22*(fade-.5)-15*rings-35*split
    wood = np.array([106,96,77] if damaged else [115,84,53])+texture[:,:,None]
    surface = np.array([65,73,57] if damaged else [44,66,53])+.52*texture[:,:,None]
    edge = np.clip(np.minimum.reduce([x,1-x,y,1-y])*40,0,1)
    wear = .35*fade+.34*grain+.31*fibres
    paint = edge*np.clip((wear-(.40 if damaged else .22))*3.5,0,1)*(1-.85*split)
    color = wood+(surface-wood)*paint[:,:,None]
    ink = mask*np.clip((wear-(.37 if damaged else .18))*5.8,0,1)*(1-.9*split)
    if damaged:
        ink *= np.clip(1-(x-.63)*1.3-(y-.4)*.23,.4,1)
    color += (np.array([199,181,140] if damaged else [233,213,163])-color)*ink[:,:,None]
    dy,dx = np.gradient(.55*fibres+.6*grain-.67*rings-1.7*split+.48*ink)
    inv = 1/np.sqrt(1+dx*dx+dy*dy)
    normal = np.stack((.5-.5*dx*inv,.5-.5*dy*inv,.5+.5*inv),axis=2)*255
    orm = np.stack((1-.24*split,.76+.12*grain-.10*paint-.05*ink,np.zeros_like(x)),axis=2)*255
    return [np.asarray(np.clip(v,0,255),dtype=np.uint8) for v in (color,normal,orm)]


if __name__ == '__main__':
    DEST.mkdir(parents=True,exist_ok=True)
    mask = emblem()
    intact,broken = face(mask,False),face(mask,True)
    for channel,front,old in zip(('Color','Normal','ORM'),intact,broken):
        # The stock mesh maps its unpainted edges, forged straps and pegs to this strip.
        atlas = Image.open(TIMBER/('T_TavernSign_'+channel+'.png')).convert('RGB')
        atlas.paste(Image.fromarray(front),(0,0))
        atlas.paste(Image.fromarray(old),(0,H))
        atlas.save(DEST/('T_HerbalistSign_'+channel+'.png'))
