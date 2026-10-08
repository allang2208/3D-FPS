"""Author the ground vector and publish the approved blade image without redrawing."""
from pathlib import Path
import math,json,sys,shutil
import subprocess
P=Path(__file__).resolve().parent
P.joinpath('Artwork').mkdir(exist_ok=True)
def ring(r,w=2):return f'<circle r="{r}" fill="none" stroke="white" stroke-width="{w}"/>'
def bagua(radius=100):
    # Clockwise: Qian, Dui, Li, Zhen, Kun, Gen, Kan, Xun. Eight distinct trigrams.
    out=[ring(99,1.5),ring(93,1),ring(53,1.5),ring(47,1),ring(37,1.7)]
    out+=['<path d="M 0 -36 A 36 36 0 0 1 0 36 A 18 18 0 0 1 0 0 A 18 18 0 0 0 0 -36" fill="white"/>',
          '<circle cy="-18" r="5" fill="white"/><circle cy="18" r="5" fill="black"/>']
    for i,code in enumerate((7,3,5,1,0,4,2,6)):
        bars=[]
        for j in range(3):
            y=-87+j*10
            if code&(1<<j):bars.append(f'<rect x="-16" y="{y}" width="32" height="5"/>')
            else:bars.extend([f'<rect x="{x}" y="{y}" width="13" height="5"/>' for x in (-16,3)])
        bars+=['<path d="M -22 -60 L -27 -65 L -29 -58 L -24 -54 M 22 -60 L 27 -65 L 29 -58 L 24 -54" fill="none" stroke="white" stroke-width="1.3"/>']
        out.append(f'<g transform="rotate({i*45})" fill="white">'+''.join(bars)+'</g>')
    return f'<g transform="scale({radius/100})">'+''.join(out)+'</g>'
def save(name,width,height,body,pixel_scale=1):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="{width*pixel_scale}" height="{height*pixel_scale}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="black"/>'+body+'</svg>'
    (P/'Artwork'/f'{name}.svg').write_text(svg,encoding='utf-8')
    subprocess.run([str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'),
                    str(P/'raster_vector.cjs'),str(P/'Artwork'/f'{name}.svg'),str(P/'Artwork'/f'{name}.png')],check=True)

# World field: concentric seal, eight trigrams, fourfold gates and fine radial ticks.
field=f'<g transform="translate(1024 1024)">{bagua(680)}{ring(955,5)}{ring(937,2)}{ring(805,2)}{ring(785,3)}'
for i in range(64):
    angle=i*360/64
    length=46 if i%8==0 else 22 if i%2==0 else 11
    field+=f'<g transform="rotate({angle})"><path d="M 0 -{875-length} V -875" stroke="white" stroke-width="{5 if i%8==0 else 2}"/></g>'
for i in range(8):
    field+=f'<g transform="rotate({i*45})"><path d="M -30 -925 L -30 -907 L 30 -907 L 30 -925 M -19 -897 L 0 -882 L 19 -897" fill="none" stroke="white" stroke-width="3"/></g>'
if '--blade-only' not in sys.argv:save('Zhenmo_Bagua_Field',2048,2048,field+'</g>')

# User-approved V4 is the image source. Historic vectors are archived in trash;
# UV cropping and seal aspect correction now happen in zhenmo_emission.hlsl.
approved=P/'BladeTalismanV4/Zhenmo_Blade_Talisman_V4_Concept.png'
shutil.copy2(approved,P/'Artwork/Zhenmo_Blade_Rune.png')
(P/'artwork_manifest.json').write_text(json.dumps({'source':'project-authored ground vector; user-approved imagegen blade','field':'Artwork/Zhenmo_Bagua_Field.svg','blade':'Artwork/Zhenmo_Blade_Rune.png','blade_revision':'BladeTalismanV4','blade_pixels':[724,2172],'blade_design_source':'BladeTalismanV4/Zhenmo_Blade_Talisman_V4_Concept.png','blade_prompt':'BladeTalismanV4/executed-prompt.txt','historic_blade_archive':'../../Docs/Archives/xuanchi-zhenyue-20261008.json','runtime_color':'gold; mask imported as grayscale'},indent=2)+'\n')
print('ZHENMO_ARTWORK_PUBLISHED')
