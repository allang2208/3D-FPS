"""Author the original Cold Steel uppercut glyph; install only this icon."""
import json
import math
import shutil
from pathlib import Path
from PIL import Image, ImageDraw

P = Path(__file__).resolve().parent
PROJECT = P.parents[2]
S = 4
N = 256*S


def points(values):
    return [(round(x*S), round(y*S)) for x, y in values]


def shaded_polygon(canvas, vertices, base, span):
    mask = Image.new('L', (N, N))
    ImageDraw.Draw(mask).polygon(points(vertices), fill=255)
    surface = Image.new('RGBA', (N, N))
    px = surface.load()
    for y in range(N):
        for x in range(N):
            light = .7*(1-y/N)+.3*(1-x/N)
            grain = 1.8*math.sin(y*1.37)+.6*math.sin(x*.09+y*.61)
            v = int(max(0, min(255, base+span*light+grain)))
            px[x,y] = (v, v, v, 255)
    canvas.paste(surface, (0,0), mask)


image = Image.new('RGBA', (N,N))
outer = [(128,10),(231,68),(231,188),(128,246),(25,188),(25,68)]
inner = [(128,22),(220,75),(220,181),(128,234),(36,181),(36,75)]
shaded_polygon(image, outer, 67, 145)
shaded_polygon(image, inner, 14, 29)
d = ImageDraw.Draw(image)
d.line(points(outer+[outer[0]]), fill=(186,186,186,255), width=2*S, joint='curve')
d.line(points(inner+[inner[0]]), fill=(5,5,5,255), width=2*S, joint='curve')
inset = [(128,28),(214,78),(214,178),(128,228),(42,178),(42,78)]
d.line(points(inset+[inset[0]]), fill=(97,97,97,255), width=S, joint='curve')

# A rising arc leads toward the upper-left, matching the first-person motion.
curve=[]
for i in range(121):
    t=i/120;v=1-t
    curve.append((v**3*183+3*v*v*t*236+3*v*t*t*188+t**3*100,
                  v**3*192+3*v*v*t*126+3*v*t*t*71+t**3*48))
d.line(points(curve),fill=(160,160,160,255),width=5*S,joint='curve')
d.polygon(points([(88,43),(112,43),(103,63)]),fill=(221,221,221,255))

# Faceted steel blade, dark fuller, guard and wrapped grip.
blade=[(83,63),(115,88),(169,159),(154,170),(100,98)]
shaded_polygon(image,blade,95,144)
d=ImageDraw.Draw(image)
d.polygon(points([(83,63),(105,95),(161,165),(154,170),(100,98)]),fill=(129,129,129,255))
d.line(points([(92,77),(159,163)]),fill=(240,240,240,255),width=S)
d.polygon(points([(146,166),(166,150),(174,155),(153,175)]),fill=(213,213,213,255))
d.polygon(points([(158,172),(168,165),(187,190),(177,197)]),fill=(65,65,65,255))
for i in range(4):
    x=162+4*i;y=176+5*i
    d.line(points([(x-1,y+2),(x+7,y-4)]),fill=(146,146,146,255),width=2*S)
d.polygon(points([(173,198),(187,187),(194,195),(180,206)]),fill=(189,189,189,255))
target=P/'sword_uppercut_cold_steel.png'
image.resize((256,256),Image.Resampling.LANCZOS).save(target)
runtime=PROJECT/'Content/ColdSteelData/Skills'/target.name
runtime.parent.mkdir(parents=True,exist_ok=True)
shutil.copy2(target,runtime)
(P/'provenance.json').write_text(json.dumps(dict(source='Original procedural vector-style artwork',
    author_script=str(Path(__file__)),paid_content=False,output=str(target),installed=str(runtime)),indent=2),encoding='utf-8')
print('UPPERCUT_ICON_SAVED '+str(runtime))
