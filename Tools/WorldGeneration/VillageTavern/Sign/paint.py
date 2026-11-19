"""Paint the cooper's sign onto two oak boards. Pixel coordinates here are face-on."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[4] / 'SourceAssets/HillsVillageTavern/Sign'
OUT.mkdir(exist_ok=True, parents=True)
W, ROW, H = 2048, 896, 2048
rng = np.random.default_rng(36601)


def noise(width, height, size):
    raw = Image.fromarray(rng.integers(0, 256, (height, width), dtype=np.uint8))
    return np.asarray(raw.resize(size, Image.Resampling.BICUBIC), dtype=np.float32) / 255


def oak(h, damaged):
    y, x = np.mgrid[:h, :W].astype(np.float32)
    y /= h
    x /= W
    size = W, h
    cloudy = noise(11, 10, size)
    streak = noise(30, max(60, h//3), size)
    fibre = noise(100, h, size)
    warp = .006 * np.sin(x*11 + 5*y) + .014 * noise(7, 10, size)
    p = y + warp + .023*(y > .5)
    for cx, cy, bend in ((.31, .22, .034), (.78, .72, -.028), (.16, .87, .019)):
        dist = ((x-cx)/.075)**2 + ((y-cy)/.095)**2
        p += bend * np.exp(-dist)*np.sin((y-cy)*20)
    rings = (.5+.5*np.sin(p*920 + 1.8*np.sin(p*143)))**5
    pores = np.clip((.21-fibre)*3, 0, 1)
    fissure = np.zeros_like(x)
    for _ in range(54 if damaged else 27):
        start = rng.uniform(-.1, .98)
        length = rng.uniform(.014, .19)
        middle = rng.uniform(.01, .99)
        along = (x-start)/length
        path = middle + .0016*np.sin(9*along + middle) + .0012*along
        width = rng.uniform(.0006, .0024) * np.clip(1-abs(along-.5)*1.8, 0, 1)
        fissure = np.maximum(fissure, np.clip((width-np.abs(y-path))*h*1.8, 0, 1))
    grey = np.array([116, 104, 83] if damaged else [113, 82, 50])
    modulation = 18*(cloudy-.5)+24*(streak-.5)+13*(fibre-.5)-16*rings-19*pores-33*fissure
    color = grey + modulation[:,:,None]
    elevation = .52*fibre+.52*streak-.65*rings-1.9*fissure
    rough = .72+.15*streak+.07*pores
    return color, elevation, rough, fissure, fibre, streak


def lettering():
    shape = Image.new('L', (W, ROW))
    pen = ImageDraw.Draw(shape)
    # Half-round cooper's barrel with broad hoops, curved staves and an elliptical head.
    outline = [(267,327),(283,296),(325,273),(399,264),(473,276),(516,300),(531,328),
               (553,396),(559,449),(555,513),(533,583),(514,612),(477,635),
               (406,646),(330,637),(296,616),(278,590),(255,517),(248,442),(251,381),(267,327)]
    pen.line(outline, fill=235, width=15, joint='curve')
    pen.ellipse((276,269,523,344),outline=239,width=13)
    for baseline,extent in ((356,134),(383,141),(531,145),(555,140)):
        pen.line([(406+int(t*extent), baseline+int((1-t*t)*23))
                  for t in np.linspace(-1,1,71)], fill=235,width=11)
    for dx in (-81,-29,27,80):
        pen.line([(406+int(dx*(.92+.29*np.sin(np.pi*t))),int(338+t*286))
                  for t in np.linspace(0,1,73)], fill=203,width=7)
    pen.arc((287,549,521,637), 12,168,fill=225,width=10)
    pen.ellipse((418,285,449,300),outline=218,width=5)
    # Position by the visible outlines of the calligraphic forms.
    font = ImageFont.truetype('C:/Windows/Fonts/simkai.ttf', 460)
    for label, center in (('酒', 955), ('馆', 1512)):
        x0,y0,x1,y1 = font.getbbox(label)
        pen.text((center-(x0+x1)/2, ROW*.504-(y0+y1)/2),label,font=font,fill=251,stroke_width=2)
    return np.asarray(shape,dtype=np.float32)/255


def border():
    shape = Image.new('L',(W,ROW))
    pen = ImageDraw.Draw(shape)
    for y in (93, ROW-94):
        for a,b in ((236,786),(1261,1812)):
            pen.line((a,y,b,y),fill=194,width=5)
        pen.polygon([(806,y),(825,y-7),(843,y),(825,y+7)],fill=206)
        pen.polygon([(1205,y),(1224,y-7),(1243,y),(1224,y+7)],fill=206)
        pen.line((856,y,1193,y),fill=152,width=3)
    return np.asarray(shape,dtype=np.float32)/255


def mix(base, tone, alpha):
    return base+(tone-base)*alpha[:,:,None]


def encode(color, elevation, rough, occlusion, metal):
    dy,dx = np.gradient(elevation)
    inv = 1/np.sqrt(1+dx*dx+dy*dy)
    normal = np.stack((.5-.5*dx*inv,.5-.5*dy*inv,.5+.5*inv),axis=2)
    orm = np.stack((occlusion,rough,metal),axis=2)
    return [np.uint8(np.clip(v,0,255)) for v in (color,normal*255,orm*255)]


def paint_face(damaged, letters, edges):
    color, elevation, rough, fissure, fibre, streak = oak(ROW,damaged)
    size = W,ROW
    yy,xx = np.mgrid[:ROW,:W]
    distance = np.minimum(np.minimum(xx, W-1-xx),np.minimum(yy,ROW-1-yy))
    mottling = noise(95, 103, size)*.35 + noise(480, 360, size)*.27 + .38*streak
    exposed = np.clip((mottling-(.47 if damaged else .28))*(5.2 if damaged else 6.5),0,1)
    edge = np.clip((distance/ROW - .029 + .037*(streak-.5))*25,0,1)
    wash = edge * (.27+.6*exposed) * (1-.60*fissure)
    painted = np.array([44,56,43] if damaged else [37,53,43]) + (20*(fibre-.5)+13*(streak-.5))[:,:,None]
    color = mix(color,painted,wash)
    worn = np.clip((mottling-(.33 if damaged else .21))*(6.2 if damaged else 8.),0,1)
    worn *= 1-np.clip(fissure*.88,0,1)
    brush = (.87+.13*noise(121,ROW,size))*worn
    edge_mask = edges*brush
    ink = letters*brush
    if damaged:
        # Right board end has weathered to exposed wood where the lower corner split away.
        scrape = np.clip((xx/W-.68)*1.5+(yy/ROW-.5)*.3+.29*(1-streak),0,.70)
        ink *= 1-scrape
    color = mix(color,np.array([182,130,71]),edge_mask)
    color = mix(color,np.array([204,177,125] if damaged else [232,207,151]),ink*.96)
    elevation += ink*.52+edge_mask*.28
    rough = rough*(1-.22*wash) - .09*ink
    return encode(color,elevation,rough,1-.24*fissure,np.zeros_like(rough))


letter_mask, border_mask = lettering(), border()
healthy = paint_face(False,letter_mask,border_mask)
ruined = paint_face(True,letter_mask,border_mask)
timber, rel, rgh, crack, fibre, streak = oak(176,False)
edge = encode(timber,rel,rgh,1-.26*crack,np.zeros_like(rgh))
size = W,80
mill = noise(175,53,size)
pits = np.clip((mill-.64)*3,0,1)
scale = noise(53,15,size)
oxide = np.clip((scale-.45)*2.7,0,1)*(.32+.65*pits)
iron = mix(np.array([67,67,61])+(25*(mill-.5))[:,:,None], np.array([106,70,44]),oxide)
metal = encode(iron,.82*mill-.65*pits,.49+.24*scale+.1*pits,1-.2*pits,.87-.68*oxide)
for i, filename in enumerate(('T_TavernSign_Color','T_TavernSign_Normal','T_TavernSign_ORM')):
    atlas = np.concatenate((healthy[i],ruined[i],edge[i],metal[i]),axis=0)
    Image.fromarray(atlas).save(OUT/(filename+'.png'))
