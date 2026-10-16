"""Author portable PBR surface data and exact lettering; no renders or tests."""
from pathlib import Path
import json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Textures"
OUT.mkdir(parents=True, exist_ok=True)
N = 4096
T = N // 4
RNG = np.random.default_rng(151026)
SPEC = [
    ("green", (55, 67, 53), .47, .05),
    ("ivory", (201, 198, 172), .30, .02),
    ("iron", (60, 62, 59), .60, .68),
    ("brass", (164, 121, 57), .34, .85),
    ("steel", (146, 154, 151), .29, .92),
    ("stone", (53, 56, 51), .82, .0),
    ("rubber", (25, 28, 27), .81, .0),
    ("leather", (72, 42, 25), .66, .0),
    ("bookgreen", (39, 51, 39), .64, .0),
    ("paper", (192, 176, 135), .85, .0),
    ("oxblood", (82, 31, 25), .63, .0),
    ("ceramic", (48, 53, 49), .46, .0),
    ("cork", (124, 89, 51), .92, .0),
    ("pages", (194, 185, 155), .85, .0),
    ("bronze", (91, 67, 40), .49, .74),
    ("white", (220, 218, 200), .35, .0),
]

def noise(scale, seed):
    rng = np.random.default_rng(seed)
    phases = rng.uniform(0, 2*math.pi, 8)
    y, x = np.mgrid[0:T, 0:T].astype(np.float32) / T
    a = np.zeros((T,T), np.float32)
    for k in range(4):
        f = scale * (2**k)
        a += (np.sin(x*f*2*math.pi+phases[k])*np.cos(y*f*2*math.pi+phases[k+4])) / (2**k)
    return a / 1.875

base = np.zeros((N,N,3), np.uint8)
orm = np.zeros_like(base)
normal = np.zeros_like(base)
regions = {}
for index, (name, col, rough, metal) in enumerate(SPEC):
    row, column = divmod(index,4)
    x0,y0 = column*T,row*T
    broad = noise(3, index+1)
    fine = noise(51,index+31)
    pores = noise(119,index+94)
    y,x = np.mgrid[0:T,0:T].astype(np.float32)
    value = broad*.035 + fine*.013
    height = fine*.003
    if name in ("iron","stone"):
        value = broad*.075+fine*.043
        height = noise(27,index+29)*.02+fine*.008
    elif name in ("brass","steel","bronze"):
        brush = np.sin(x*.33+noise(7,index+82)*2)
        value = broad*.03+brush*.012
        height = brush*.0015
    elif name in ("leather","bookgreen","oxblood"):
        height = pores*.005+fine*.003
        value = broad*.055+fine*.018
    elif name=="cork":
        pits = np.maximum(0, fine-.32)
        value = broad*.13+fine*.09-pits*.45
        height = fine*.012
    elif name=="pages":
        lines=np.sin(y*.54+np.sin(x*.006)*.3)
        value=broad*.025+lines*.04
        height=lines*.0018
    elif name=="ceramic":
        value=broad*.04+fine*.012
        height=fine*.001
    rgb=np.clip(np.array(col)[None,None,:]*(1+value[:,:,None]),0,255).astype(np.uint8)
    o=np.empty((T,T,3),np.uint8)
    o[:,:,0]=255
    o[:,:,1]=np.clip((rough+broad*.025+fine*.018)*255,0,255).astype(np.uint8)
    o[:,:,2]=int(metal*255)
    # Derivatives of smooth, band-limited height data.
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*2
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*2
    nn=np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
    nn/=np.linalg.norm(nn,axis=-1,keepdims=True)
    n=np.clip((nn*.5+.5)*255,0,255).astype(np.uint8)
    base[y0:y0+T,x0:x0+T]=rgb
    orm[y0:y0+T,x0:x0+T]=o
    normal[y0:y0+T,x0:x0+T]=n
    regions[name]=[x0,y0,x0+T,y0+T]
for kind, data in (("BaseColor",base),("ORM",orm),("Normal",normal)):
    Image.fromarray(data).save(OUT/f"T_PotionWorkbench_{kind}.png")

# Labels are original vector/text compositions, not concept-image projections.
labels=Image.new("RGB",(2048,2048),(205,189,148))
d=ImageDraw.Draw(labels)
font_dir=Path("C:/Windows/Fonts")
def font(size, bold=False):
    return ImageFont.truetype(str(font_dir/("georgiab.ttf" if bold else "georgia.ttf")),size)
titles=[
    ("REDVEIN","EXTRACT","01"),
    ("SILVERLEAF","ESSENCE","02"),
    ("PURE BASE","SOLVENT","03"),
    ("BLUE MARROW","CRYSTALS","04"),
    ("CATALYST","ACTIVE","05"),
    ("DISTILLATE","CLEAR","06"),
    ("MOON HERB","DRIED","07"),
    ("STABILIZER","COMPOUND","08"),
    ("REAGENTS","DRY STORAGE","09"),
    ("ARCANE","FORMULAE","10"),
    ("POTION","WORKBENCH","11"),
    ("CENTRIFUGE","8 POSITION","12"),
    ("ROOT SALT","REFINED","13"),
    ("ETHER","TINCTURE","14"),
    ("SAMPLES","BALANCED SET","15"),
    ("BATCH","SEALED","16"),
]
for i,(a,b,num) in enumerate(titles):
    xx=(i%4)*512;yy=(i//4)*512
    d.rectangle((xx+18,yy+18,xx+494,yy+494),fill=(204,189,151),outline=(94,72,39),width=5)
    d.rectangle((xx+30,yy+30,xx+482,yy+482),outline=(132,107,65),width=2)
    d.line((xx+72,yy+125,xx+440,yy+125),fill=(105,77,39),width=3)
    d.text((xx+256,yy+81),"APOTHECARY",font=font(25),fill=(76,58,32),anchor="mm")
    d.text((xx+256,yy+194),a,font=font(38,True),fill=(59,43,24),anchor="mm")
    d.text((xx+256,yy+252),b,font=font(25),fill=(76,58,32),anchor="mm")
    d.line((xx+72,yy+299,xx+440,yy+299),fill=(105,77,39),width=2)
    d.ellipse((xx+216,yy+332,xx+296,yy+412),outline=(105,77,39),width=2)
    d.text((xx+256,yy+372),num,font=font(31),fill=(76,58,32),anchor="mm")
    d.text((xx+256,yy+451),"RESEARCH  /  KEEP SEALED",font=font(17),fill=(105,77,39),anchor="mm")
labels.save(OUT/"T_PotionWorkbench_Labels.png")
manifest={"atlas_size":N,"regions":regions,"labels":titles,
          "provenance":"Original numeric surface authoring and exact vector/text labels. Wood maps extracted from the existing approved project workbench.",
          "normal_convention":"OpenGL +Y; invert green if imported with a DirectX normal convention.",
          "channels":{"ORM":{"R":"ambient occlusion (constant 1, not baked scene AO)","G":"roughness","B":"metallic"}}}
(ROOT/"texture_manifest.json").write_text(json.dumps(manifest,indent=2),"utf8")
print("POTION_TEXTURE_AUTHORING_COMPLETE",flush=True)
