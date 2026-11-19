"""Build one PBR draw atlas for the folding tables board and its fallen counterpart."""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / 'SourceAssets'
OUT = SRC / 'HillsVillageTavern/TableGame'
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 2048
CELL = 512
RNG = np.random.default_rng(2279)
colour = np.zeros((SIZE, SIZE, 3), dtype=np.uint8)
normal = np.zeros_like(colour)
orm = np.zeros_like(colour)


def noise(n, cx, cy):
    seed = RNG.integers(0, 255, (cy, cx), dtype=np.uint8)
    return np.asarray(Image.fromarray(seed).resize((n, n), Image.Resampling.BICUBIC), float)/255.-.5


def rgb(array):
    return np.uint8(np.clip(array, 0, 255))


def normal_from(height):
    dy, dx = np.gradient(height)
    inv = 1./np.sqrt(dx*dx + dy*dy + 1.)
    return rgb(np.stack((127.5-127.5*dx*inv, 127.5+127.5*dy*inv, 127.5+127.5*inv), -1))


def masks(rough, metal=0, ao=255):
    return rgb(np.stack(np.broadcast_arrays(ao, rough, metal), axis=-1))


def load(path):
    with Image.open(path) as image:
        return np.asarray(image.convert('RGB').resize((CELL, CELL), Image.Resampling.LANCZOS), float)


def install(tile, base, normals, surface):
    x = CELL*(tile % 4)
    y = 1024+CELL*(tile//4)
    for dst, value in ((colour, base), (normal, normals), (orm, surface)):
        dst[y:y+CELL, x:x+CELL] = rgb(value)


def wood(tile, folder, stem, tint, lightness, roughness, end=False):
    base=load(folder/(stem+('_Color.png' if end else '_BaseColor.png')))
    normals=load(folder/(stem+'_Normal.png'))
    packed=load(folder/(stem+('_ORM.png' if end else '_RHAOM.png')))
    lum=np.mean(base,axis=-1)
    grain=np.clip((lum+18)/(np.median(lum)+18),.44,1.62)
    albedo=(grain[...,None]**lightness)*np.array(tint)
    # The village's cross-cut plate is ORM, the remaining wood donors use red roughness.
    old_rough=packed[:,:,1 if end else 0]
    surface=masks(np.clip(roughness+(old_rough-old_rough.mean())*.44,60,238))
    install(tile,albedo,normals,surface)


fresh=SRC/'ApprenticeStaff20260927/SolidRepairV19/Inputs'
wood(0, fresh, 'T_WoodSurface_00A', (129,88,48), .82, 139)
wood(1, fresh, 'T_WoodSurface_00A', (68,45,30), .72, 120)
wood(2, SRC/'HillsVillageTavern/Furniture', 'RottenWoodSurface_00A', (103,90,70), .90, 201)
wood(3, SRC/'HillsVillageCarpenter/Props/Authored', 'Cut', (132,96,63), .82, 165, True)

n=CELL
y,x=np.mgrid[:n,:n]/n
pores=np.maximum(noise(n,124,139)-.19,0)
flecks=noise(n,40,30)*.26+noise(n,5,5)*.67+noise(n,316,314)*.1
iron=np.clip(1+flecks*.45-pores*.55,.5,1.4)
rust=np.clip((flecks-.16)*5.,0,1)
install(4, iron[...,None]*[72,66,56]+rust[...,None]*[46,8,-6],normal_from(2.2*pores+noise(n,300,310)*.13),
        masks(104+70*rust+pores*100,192-122*rust,250-pores*36))
bone=1+noise(n,12,3)*.075+noise(n,7,80)*.073+noise(n,242,225)*.062
install(5,bone[...,None]*[196,178,138],normal_from(noise(n,82,160)*.6),masks(112+pores*174))
thread=1+noise(n,42,330)*.25+noise(n,16,4)*.15
install(6,thread[...,None]*[75,54,33],normal_from(noise(n,56,300)*1.5),masks(166+pores*88))

# Six die faces fit in the last atlas tile. A depressed ring surrounds each dark pip.
die_color=bone[...,None]*[201,181,142]
die_depth=noise(n,82,92)*.15
die_rough=112+pores*70
patterns={1:[(0,0)],2:[(-1,-1),(1,1)],3:[(-1,-1),(0,0),(1,1)],
          4:[(-1,-1),(1,-1),(-1,1),(1,1)],5:[(-1,-1),(1,-1),(0,0),(-1,1),(1,1)],
          6:[(-1,-1),(1,-1),(-1,0),(1,0),(-1,1),(1,1)]}
for number, coords in patterns.items():
    col=(number-1)%3
    row=(number-1)//3
    px=(x*3-col-.5)
    py=(y*2-row-.5)
    for ax,ay in coords:
        r=np.hypot(px-ax*.24,py-ay*.24)
        ink=np.clip((.072-r)/.011,0,1)*.91
        ring=np.clip(1-np.abs(r-.091)/.012,0,1)
        die_color=die_color*(1-ink[...,None])+np.array([55,40,29])*ink[...,None]
        die_color*=1-.32*ring[...,None]
        die_depth-=ink*2.7+ring*.94
        die_rough+=ink*32
install(7,die_color,normal_from(die_depth),masks(die_rough))


def field(damaged):
    n=1024
    y,x=np.mgrid[:n,:n]/(n-1)
    pores=np.clip((noise(n,283,272)-.185)*1.9,0,1)
    patina=noise(n,7,8)*.48+noise(n,38,29)*.24+noise(n,124,112)*.17
    height=noise(n,256,260)*.65-pores*.94+patina*.7
    field_tone=(97,81,57) if damaged else (157,124,79)
    base=np.array(field_tone)[None,None,:]*(1+patina[...,None]*.38-pores[...,None]*.14)
    ends=np.abs(y-.5)*2
    border=(np.minimum.reduce([x,1-x,y,1-y]) < .023)
    base*=1-.21*border[...,None]
    rough=157+patina*38+pores*37+(29 if damaged else 0)
    pitch=(.958/6)
    for row in range(2):
        depth=(y-.045) if not row else (1-y-.045)
        for i in range(6):
            centre=.021+pitch*(i+.5)
            width=.073*(1-depth/.387)
            sd=(width-np.abs(x-centre))
            crest=np.clip(sd*n+.5,0,1)*np.clip(depth*n,0,1)*np.clip((.387-depth)*n,0,1)
            pale=(i+row)%2==0
            tint=([148,133,94] if pale else [76,62,47]) if damaged else ([190,162,107] if pale else [112,59,40])
            pigment=(1+patina*.26-pores*.14)[...,None]*tint
            base=base*(1-crest[...,None])+pigment*crest[...,None]
            edge=np.clip(1-np.abs(sd)*n/1.4,0,1)*(depth>=0)*(depth<.387)
            base*=1-.19*edge[...,None]
            height-=edge*1.17
    edge=np.minimum.reduce([x,1-x,y,1-y])
    for inset in (.029,.037):
        rule=np.clip(1-np.abs(edge-inset)*n/1.35,0,1)
        base*=1-.41*rule[...,None]
        height-=rule*1.1
    # Fine irregular scoring and a faded tidemark across the abandoned playing surface.
    scratches=Image.new('L',(n,n))
    pen=ImageDraw.Draw(scratches)
    count=185 if damaged else 34
    for i in range(count):
        cx,cy=RNG.uniform(14,n-14,2)
        length=RNG.uniform(6,74)
        skew=RNG.uniform(-.5,.5)
        pen.line([(cx,cy),(cx+length*.53,cy+length*skew*.49+1),(cx+length,cy+length*skew)],fill=int(RNG.uniform(18,115)),width=1)
    sc=np.asarray(scratches,float)/255.
    base+=sc[...,None]*[50,44,32]
    height-=sc*1.2
    if damaged:
        watermark=np.clip((.21+noise(n,8,8)*.18-y)*10,0,1)
        base*=1-.20*watermark[...,None]
        rough+=9*watermark
    return rgb(base),normal_from(height),masks(rough,0,255-14*pores)

for variant in (0,1):
    for tile,atlas in zip(field(bool(variant)),(colour,normal,orm)):
        atlas[:1024,1024*variant:1024*(variant+1)] = tile

for name, atlas in (('Color',colour),('Normal',normal),('ORM',orm)):
    Image.fromarray(atlas).save(OUT/('T_TavernTables_'+name+'.png'))
