"""Original 52-card artwork, back and result strip. Texture production only; no preview render."""
import json
import math
import runpy
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'Export' / 'Textures'
OUT.mkdir(parents=True, exist_ok=True)
W, H = 450, 630
GOLD = (185, 140, 67, 228)
INK = (22, 31, 43, 245)
RED = (172, 36, 48, 245)
SERIF = 'C:/Windows/Fonts/timesbd.ttf'
CJK = 'C:/Windows/Fonts/msyhbd.ttc'


def font(size, chinese=False):
    return ImageFont.truetype(CJK if chinese else SERIF, int(size))


def suit(draw, x, y, size, kind, color, inverted=False):
    if kind == 1:
        draw.polygon([(x, y-size*.65), (x+size*.45, y), (x, y+size*.65), (x-size*.45, y)], fill=color)
    elif kind == 0:
        r = size*.28
        for dx, dy in [(0, -.24), (-.25, .06), (.25, .06)]:
            cx, cy = x+dx*size, y+dy*size
            draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=color)
        draw.polygon([(x-size*.2, y+size*.58), (x+size*.2, y+size*.58), (x, y-size*.05)], fill=color)
    else:
        points = []
        for n in range(100):
            t = n*2*math.pi/100
            px = 16*math.sin(t)**3/32
            py = -(13*math.cos(t)-5*math.cos(2*t)-2*math.cos(3*t)-math.cos(4*t))/32
            if kind == 3:
                py = -py
            if inverted:
                px, py = -px, -py
            points.append((x+px*size, y+py*size))
        draw.polygon(points, fill=color)
        if kind == 3:
            draw.polygon([(x-size*.2, y+size*.6), (x+size*.2, y+size*.6), (x, y+size*.1)], fill=color)


def court(card, rank, kind, color):
    """Original mirrored geometric court figures; no external face illustrations."""
    half = Image.new('RGBA', (260, 245))
    d = ImageDraw.Draw(half)
    d.polygon([(30,235),(60,158),(130,135),(200,158),(230,235)], fill=(32,52,72,238), outline=GOLD, width=4)
    d.polygon([(76,177),(111,203),(130,164),(151,203),(183,177),(162,240),(98,240)], fill=color, outline=GOLD, width=3)
    d.ellipse((92,77,167,157), fill=(221,194,143,238), outline=GOLD, width=3)
    # Profile, hair, brow and jewelry, distinct between jack, queen and king.
    d.polygon([(100,85),(113,70),(150,75),(167,97),(151,94),(148,126),(134,145),(112,136)], fill=(39,42,49,240))
    d.polygon([(136,98),(150,99),(154,114),(169,119),(151,123),(153,133),(135,135)], fill=(221,194,143,245))
    d.line([(143,109),(152,110)], fill=INK, width=3)
    d.line([(145,127),(152,127)], fill=INK, width=2)
    if rank == 12:
        d.arc((92,85,160,172), 62, 175, fill=GOLD, width=6)
        d.ellipse((131,128,140,137), fill=GOLD)
    if rank == 13:
        d.polygon([(131,135),(150,131),(147,153),(136,158)], fill=(57,47,45,242))
    tips = 5 if rank == 13 else 3
    crown = [(94,80)]
    for n in range(tips):
        crown += [(93+n*17,55-(n%2)*9),(102+n*17,74)]
    crown += [(169,80),(165,91),(98,91)]
    d.polygon(crown, fill=GOLD, outline=(235,200,117,245), width=2)
    if rank == 11:
        d.line([(198,225),(178,67)], fill=GOLD, width=7)
        d.polygon([(178,46),(186,73),(174,83),(169,70)], fill=GOLD)
    elif rank == 12:
        for angle in range(6):
            t = angle*math.pi/3
            cx, cy = 64+13*math.cos(t), 97+13*math.sin(t)
            d.ellipse((cx-8,cy-8,cx+8,cy+8),fill=RED)
        d.line([(64,119),(67,217)],fill=GOLD,width=4)
    else:
        d.line([(195,82),(197,230)], fill=GOLD, width=6)
        d.ellipse((183,63,207,91), fill=GOLD)
    suit(d,130,216,33,kind,(230,204,151,235))
    card.alpha_composite(half,(95,119))
    card.alpha_composite(half.rotate(180),(95,266))


def face(rank, kind):
    image = Image.new('RGBA', (W,H))
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((0,0,W-1,H-1),radius=22,fill=(225,233,240,102),outline=GOLD,width=5)
    d.rounded_rectangle((13,13,W-14,H-14),radius=14,outline=(175,143,90,120),width=2)
    color = RED if kind in (1,2) else INK
    label = {11:'J',12:'Q',13:'K',14:'A'}.get(rank,str(rank))
    corner = Image.new('RGBA',(80,135))
    cd = ImageDraw.Draw(corner)
    cd.text((40,5),label,font=font(62 if rank!=10 else 48),anchor='mt',fill=color,stroke_width=0)
    suit(cd,40,104,40,kind,color)
    image.alpha_composite(corner,(17,14))
    image.alpha_composite(corner.rotate(180),(W-97,H-149))
    if rank in (11,12,13):
        d.rounded_rectangle((92,115,358,515),radius=10,outline=GOLD,width=4)
        court(image,rank,kind,color)
    elif rank==14:
        suit(d,W/2,H/2,182,kind,color)
        d.text((W/2,H*.71),'DEALER',font=font(23),anchor='mt',fill=GOLD)
    else:
        coords=[]
        if rank in (2,3):
            coords=[(0,-.25),(0,.25)]+([(0,0)] if rank==3 else [])
        elif rank in (4,5):
            coords=[(x,y) for x in (-.205,.205) for y in (-.25,.25)]
            if rank==5:coords.append((0,0))
        elif rank in (6,7,8):
            coords=[(x,y) for x in (-.205,.205) for y in (-.25,0,.25)]
            if rank>=7:coords.append((0,-.125))
            if rank==8:coords.append((0,.125))
        else:
            coords=[(x,y) for x in (-.205,.205) for y in (-.27,-.09,.09,.27)]
            coords+=([(0,0)] if rank==9 else [(0,-.18),(0,.18)])
        for x,y in coords:suit(d,W*(.5+x),H*(.5+y),64,kind,color,y>0)
    return image


atlas = Image.new('RGBA',(4096,2048))
manifest = []
for kind in range(4):
    for rank in range(2,15):
        index = kind*13+rank-2
        left, right = round((rank-2)*4096/13), round((rank-1)*4096/13)
        atlas.alpha_composite(face(rank,kind).resize((right-left,512),Image.Resampling.LANCZOS),(left,kind*512))
        manifest.append({'id':index,'suit':['clubs','diamonds','hearts','spades'][kind],'rank':rank})
atlas.save(OUT/'T_DealerFaces.png')

back = Image.new('RGBA',(W,H))
d = ImageDraw.Draw(back)
d.rounded_rectangle((0,0,W-1,H-1),radius=22,fill=(17,34,55,115),outline=GOLD,width=5)
d.rounded_rectangle((18,18,W-19,H-19),radius=12,outline=GOLD,width=3)
for y in range(45,H-30,32):
    for x in range(42,W-30,32):
        d.polygon([(x,y-12),(x+10,y),(x,y+12),(x-10,y)],outline=(142,127,93,145),width=1)
d.ellipse((130,221,320,409),fill=(15,31,49,225),outline=GOLD,width=4)
suit(d,W/2,H/2,115,3,GOLD)
back.resize((512,1024),Image.Resampling.LANCZOS).save(OUT/'T_DealerBack.png')

# Keep the full-deck authoring entry on the current English, glyph-only Infernal recipe.
runpy.run_path(str(ROOT/'InfernalV2/author_titles.py'))['build_title_assets']()
Image.open(ROOT/'InfernalV2/Export/T_DealerInfernalTitles.png').save(OUT/'T_DealerResults.png')
(ROOT/'deck.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(ROOT/'art-receipt.json').write_text(json.dumps({'complete':True,'cards':52,'atlases':[str(p) for p in OUT.glob('*.png')],
    'provenance':'Original procedural geometry and illustrations; system fonts rasterized, font files not distributed.',
    'preview_rendered':False,'runtime_tested':False},indent=2),encoding='utf-8')
print('DEALER_ART_SAVED cards=52 textures=3 preview=false')
