"""Produce desktop-prop PBR source maps; no preview renders or engine session."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PROJECT = Path('D:/FPS3D/FPSGAME')
OUT = PROJECT/'SourceAssets/GunWorkbenchPolish20260928/Authored'
TEX = OUT/'Textures'
TEX.mkdir(parents=True, exist_ok=True)
LIBRARY = PROJECT/'SourceAssets/DungeonWorkshopSurface20260921/Authored/Textures'
RNG = np.random.default_rng(92826)
surfaces = {}

def coarse_noise(size, cells):
    field = RNG.integers(0, 256, (cells, cells), dtype=np.uint8)
    return np.asarray(Image.fromarray(field).resize((size, size), Image.Resampling.BICUBIC), dtype=np.float32)/255-.5

def write_maps(name, color, roughness, height, metallic, normal_slope=1):
    size = roughness.shape[0]
    color = np.broadcast_to(color, (*roughness.shape, 3))
    maps = {}
    def save(channel, array):
        path = TEX/(name+'_'+channel+'.png')
        Image.fromarray(np.rint(np.clip(array, 0, 1)*255).astype(np.uint8)).save(path)
        maps[channel] = str(path)
    save('BaseColor', color)
    # R=unoccluded surface, G=roughness, B=metallic. Geometry supplies contact AO.
    save('ORM', np.stack([np.ones_like(roughness), roughness, np.full_like(roughness, metallic)], axis=-1))
    dy, dx = np.gradient(height)
    normal = np.stack([-dx*normal_slope, dy*normal_slope, np.ones_like(dx)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    save('Normal', normal*.5+.5)  # OpenGL normal; Unreal import flips green once.
    return {'maps': maps, 'normal_strength': 1, 'roughness_scale': 1, 'roughness_bias': 0,
            'color_tint': [1, 1, 1], 'metallic': metallic}

def library(material, key, tint, rough_scale, rough_bias, normal, metallic):
    surfaces[material] = {'maps': {c: str(LIBRARY/(key+'_'+c+'.png')) for c in ['BaseColor','Roughness','Normal']},
        'color_tint': tint, 'roughness_scale': rough_scale, 'roughness_bias': rough_bias,
        'normal_strength': normal, 'metallic': metallic}

# Existing authored machining maps: preserve source provenance and avoid new downloads.
library('GW3_Steel', 'GroundSteel', [1.05,1.10,1.15], .50,.12,.28,1)
library('GW3_DarkSteel', 'GroundSteel', [.18,.23,.28], .58,.14,.32,1)
library('GW3_Brass', 'GroundSteel', [1.13,.70,.26], .54,.12,.24,1)
library('GW3_Blue', 'GroundSteel', [.055,.23,.39], .60,.10,.23,1)
library('GW3_Rubber', 'Grip', [.63,.69,.66], .76,.16,.37,0)

# Work pad: low-amplitude molded silicone grain with softened handling marks.
n=2048
y,x=np.mgrid[0:n,0:n].astype(np.float32)/n
low=coarse_noise(n,18); grain=coarse_noise(n,640)
rub=np.exp(-(((x-.56)/.30)**2+((y-.48)/.27)**2)*2)
scuffs=Image.new('L',(n,n),0); d=ImageDraw.Draw(scuffs)
for _ in range(40):
    px=int(RNG.uniform(.20,.82)*n);py=int(RNG.uniform(.18,.82)*n)
    d.line((px,py,px+int(RNG.uniform(8,60)),py+int(RNG.uniform(-12,12))),fill=int(RNG.uniform(18,56)),width=1)
scuff=np.asarray(scuffs.filter(ImageFilter.GaussianBlur(.65)),dtype=np.float32)/255
color=np.array([.171,.182,.176],dtype=np.float32)+(grain*.009+low*.019+scuff*.025)[...,None]
surfaces['GW3_Mat']=write_maps('SiliconePad',color,.80+grain*.052+low*.035-rub*.055-scuff*.08,grain*.20+low*.10-scuff*.15,0,1.3)

# Spun dishes: the ring pattern affects reflections, not black painted circles.
radius=np.sqrt((x-.5)**2+(y-.5)**2)
grain=coarse_noise(n,920);low=coarse_noise(n,24)
turning=np.sin(radius*2*np.pi*760 + .16*np.sin(radius*270))
scratch_img=Image.new('L',(n,n),0);d=ImageDraw.Draw(scratch_img)
for _ in range(16):
    px,py=RNG.uniform(.28,.72,2)*n;length=RNG.uniform(25,140);angle=RNG.uniform(0,2*np.pi)
    d.line((px,py,px+np.cos(angle)*length,py+np.sin(angle)*length),fill=RNG.integers(12,42).item(),width=1)
scratches=np.asarray(scratch_img.filter(ImageFilter.GaussianBlur(.6)),dtype=np.float32)/255
color=np.array([.735,.756,.775],dtype=np.float32)+(low*.022+grain*.007+scratches*.028)[...,None]
surfaces['GW3_SpunSteel']=write_maps('SpunSteel',color,.30+turning*.028+low*.045+scratches*.16,turning*.024+grain*.01-scratches*.12,1,1)

n=1024
y,x=np.mgrid[0:n,0:n].astype(np.float32)/n
grain=coarse_noise(n,410);low=coarse_noise(n,16)
# Replaceable mallet face remains polymer, with soft surface variation.
surfaces['GW3_Nylon']=write_maps('Nylon',np.array([.842,.846,.803])+(grain*.010+low*.028)[...,None],.50+grain*.07+low*.035,grain*.10,0,1)
# Oil bottle: amber resin, deliberately opaque to keep its tiny prop inexpensive.
surfaces['GW3_Amber']=write_maps('AmberResin',np.array([.43,.235,.063])+(low*.009+grain*.002)[...,None],.235+grain*.008+low*.025,grain*.009,0,1)

# Actual print artwork, with aspect ratio matched to the wraparound paper sleeve.
label=Image.new('RGB',(2048,512),(202,200,181));d=ImageDraw.Draw(label)
font_dir=Path('C:/Windows/Fonts')
def font(size,bold=False):return ImageFont.truetype(str(font_dir/('arialbd.ttf' if bold else 'arial.ttf')),size)
ink=(40,49,43);accent=(128,113,70)
d.rectangle((0,22,2047,31),fill=ink);d.rectangle((0,480,2047,489),fill=ink)
for cx in (512,1536):
    d.text((cx,64),'MAINTENANCE',font=font(37,True),fill=ink,anchor='mt')
    d.text((cx,104),'OIL',font=font(152,True),fill=ink,anchor='mt')
    d.rectangle((cx-164,290,cx+164,294),fill=accent)
    d.text((cx,319),'PRECISION TOOL CARE',font=font(24),fill=ink,anchor='mt')
    d.text((cx,394),'100 mL',font=font(43,True),fill=ink,anchor='mt')
paper=np.asarray(label,dtype=np.float32)/255
paper_noise=RNG.normal(0,.0017,(512,2048)).astype(np.float32)
printed=np.mean(paper,axis=-1)<.5
surfaces['GW3_Label']=write_maps('MaintenanceLabel',paper+paper_noise[...,None],.74+paper_noise*5-printed*.07,paper_noise*.4,0,.55)
surfaces['GW3_Index']={'color':[.17,.19,.18], 'roughness':.77,'metallic':0}

manifest={'materials': surfaces, 'provenance': [
    {'source':str(LIBRARY), 'usage':'Reuse existing project GroundSteel and Grip base/roughness/OpenGL-normal texture sets; originals unchanged.'},
    {'source':str(Path(__file__)), 'usage':'Deterministic locally authored silicone, spun steel, nylon, amber resin and printed label PBR maps. No external acquisition.'}],
    'normal_convention':'OpenGL; flip green on Unreal import', 'max_texture_dimension':2048,
    'tests_run':False, 'renders_run':False}
(OUT/'surface-materials.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('WORKBENCH_PBR_AUTHORED',len(surfaces),'material recipes')
